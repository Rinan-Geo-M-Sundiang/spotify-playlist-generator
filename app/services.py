
from flask import jsonify, request
from flask_jwt_extended import jwt_required
from app import db
from app.models import Playlist, Track, Favorite, UserRating, TrackComment
from app.serializers import playlists_schema, track_schema, playlist_schema, track_comment_schema, \
    track_comments_schema, tracks_schema
from app.extensions import sp, sp_oauth  # Changed import source
from datetime import datetime

from flask_jwt_extended import get_jwt_identity




import logging
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from spotipy.exceptions import SpotifyException
@jwt_required()
def create_playlist(data):
    """Create a playlist both locally and on Spotify."""
    try:
        user_id = get_jwt_identity()
        if isinstance(user_id, dict):
            user_id = user_id.get("id")
        else:
            user_id = user_id
        name = data.get("name")
        description = data.get("description", "")
        is_public = data.get("public", False)
        is_collaborative = data.get("collaborative", False)

        if not user_id or not name:
            return jsonify({"error": "Missing playlist name"}), 400

        # Force token refresh if needed
        token_info = sp_oauth.get_cached_token()
        if not token_info or sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            sp.set_auth(token_info['access_token'])

        spotify_user = sp.current_user()
        spotify_user_id = spotify_user["id"]

        # Create Spotify playlist
        spotify_playlist = sp.user_playlist_create(
            user=spotify_user_id,
            name=name,
            public=is_public,
            collaborative=is_collaborative,
            description=description
        )

        # Save to database
        new_playlist = Playlist(
            user_id=user_id,
            name=name,
            description=description,
            spotify_id=spotify_playlist["id"]
        )
        db.session.add(new_playlist)
        db.session.commit()

        return jsonify({
            "message": "Playlist created successfully!",
            "playlist": playlist_schema.dump(new_playlist)
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Playlist creation failed: {str(e)}")
        return jsonify({"error": "Failed to create playlist", "details": str(e)}), 500

@jwt_required()
def get_playlists():
    """Retrieve all playlists for the authenticated user."""
    user_id = get_jwt_identity()
    if isinstance(user_id, dict):
        user_id = user_id.get("id")
    else:
        user_id = user_id
    playlists = Playlist.query.filter_by(user_id=user_id).all()

    if not playlists:
        return jsonify({"message": "No playlists found"}), 200

    return jsonify(playlists_schema.dump(playlists)), 200


@jwt_required()
def add_track_to_playlist(playlist_id, data):
    """Add a track to a specific playlist (Both Local & Spotify)."""
    try:
        user_id = get_jwt_identity()
        if isinstance(user_id, dict):
            user_id = user_id.get("id")
        else:
            user_id = user_id
        playlist = Playlist.query.filter_by(id=playlist_id, user_id=user_id).first()

        if not playlist:
            return jsonify({"error": "Playlist not found"}), 404

        if not playlist.spotify_id:
            return jsonify({"error": "This playlist does not have a linked Spotify ID"}), 400
        #  Validate incoming data
        track_name = data.get("name", "").strip()
        artist_name = data.get("artist", "").strip()
        album_name = data.get("album", "").strip() if data.get("album") else None

        if not track_name or not artist_name:
            return jsonify({"error": "Invalid track name or artist"}), 400

        #  Search Track on Spotify
        search_query = f"track:{track_name} artist:{artist_name}"
        search_result = sp.search(q=search_query, type="track", limit=1)

        if not search_result["tracks"]["items"]:
            return jsonify({"error": "Track not found on Spotify"}), 404

        spotify_track_uri = search_result["tracks"]["items"][0]["uri"]
        # Extract Spotify Track ID from URI (NEW)
        spotify_track_id = spotify_track_uri.split(":")[-1]  # Get last part of "spotify:track:abc123"
        #  Add Track to Spotify Playlist
        sp.playlist_add_items(playlist_id=playlist.spotify_id, items=[spotify_track_uri])

        #  Save to Local Database
        new_track = Track(
            name=track_name,
            artist=artist_name,
            album=album_name if album_name else None,
            playlist_id=playlist.id,
            spotify_track_id=spotify_track_id  # Store Spotify ID (NEW)
        )
        db.session.add(new_track)
        db.session.commit()

        return jsonify({
            "message": "Track added successfully!",
            "track": track_schema.dump(new_track),
            "spotify_track_uri": spotify_track_uri,
            "spotify_playlist_id": playlist.spotify_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add track", "details": str(e)}), 500


def remove_track_from_playlist(data):
    """Remove track by playlist/track names"""
    user_id = get_jwt_identity()
    if isinstance(user_id, dict):
        user_id = user_id.get("id")
    else:
        user_id = user_id
    playlist_name = data.get("playlist_name")
    track_name = data.get("track_name")

    if not all([playlist_name, track_name]):
        return jsonify({"error": "Missing playlist/track names"}), 400

    try:
        # Get playlist with user ownership check
        playlist = Playlist.query.filter_by(
            user_id=user_id,
            name=playlist_name
        ).first()

        if not playlist:
            return jsonify({"error": "Playlist not found"}), 404

        # Find track with case-insensitive search
        track = Track.query.filter(
            Track.playlist_id == playlist.id,
            Track.name.ilike(track_name)
        ).first()

        if not track:
            return jsonify({"error": "Track not found"}), 404

        # Validate Spotify references
        spotify_errors = []
        if not playlist.spotify_id:
            spotify_errors.append("Playlist not linked to Spotify")

        if not track.spotify_track_id:
            spotify_errors.append("Track missing Spotify reference")

        # Only attempt Spotify removal if both IDs exist
        if playlist.spotify_id and track.spotify_track_id:
            try:
                # Construct proper Spotify URI
                track_uri = f"spotify:track:{track.spotify_track_id}"

                # Verify URI format
                if len(track.spotify_track_id) != 22:  # Spotify IDs are 22 chars
                    raise ValueError("Invalid Spotify track ID format")

                # Remove from Spotify
                sp.playlist_remove_all_occurrences_of_items(
                    playlist_id=playlist.spotify_id,
                    items=[track_uri]  # Note: items should be list of URIs, not dicts
                )
            except Exception as e:
                return jsonify({
                    "error": "Spotify removal failed",
                    "details": str(e),
                    "debug_info": {
                        "spotify_playlist_id": playlist.spotify_id,
                        "spotify_track_id": track.spotify_track_id,
                        "constructed_uri": track_uri
                    }
                }), 500

        # Local database removal
        db.session.delete(track)
        db.session.commit()

        return jsonify({
            "message": "Track removed",
            "playlist": playlist.name,
            "track": track.name,
            "spotify_errors": spotify_errors if spotify_errors else None
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Removal failed",
            "details": str(e),

        }), 500



def get_tracks_from_playlist(playlist_id):
    """Retrieve all tracks from a playlist."""
    user_id = get_jwt_identity()
    if isinstance(user_id, dict):
        user_id = user_id.get("id")
    else:
        user_id = user_id
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=user_id).first()

    if not playlist:
        return jsonify({"error": "Playlist not found"}), 404

    tracks = Track.query.filter_by(playlist_id=playlist.id).all()

    if not tracks:
        return jsonify({"message": "No tracks found in this playlist"}), 200

    # Use the correct schema for multiple tracks and wrap in a proper response structure
    return jsonify({
        "tracks": tracks_schema.dump(tracks)
    }), 200


# In services.py
def handle_song_feedback(data):
    """Handle song ratings using playlist/track names"""
    user_id = get_jwt_identity()
    if isinstance(user_id, dict):
        user_id = user_id.get("id")
    else:
        user_id = user_id
    playlist_name = data.get("playlist_name")
    track_name = data.get("track_name")
    rating = data.get("rating")

    if not all([playlist_name, track_name, rating]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Get playlist by name
        playlist = Playlist.query.filter_by(
            user_id=user_id,
            name=playlist_name
        ).first()

        if not playlist:
            return jsonify({"error": "Playlist not found"}), 404

        # Get track by name in playlist
        track = Track.query.filter_by(
            playlist_id=playlist.id,
            name=track_name
        ).first()

        if not track:
            return jsonify({"error": "Track not found in playlist"}), 404

        # Add validation for Spotify ID (NEW)
        if not track.spotify_track_id:
            return jsonify({
                "error": "Track missing Spotify reference",
                "solution": "Re-add this track to generate proper ID"
            }), 400

        # Update or create rating
        existing = UserRating.query.filter_by(
            user_id=user_id,
            spotify_track_id=track.spotify_track_id
        ).first()

        if existing:
            existing.rating = rating
        else:
            db.session.add(UserRating(
                user_id=user_id,
                spotify_track_id=track.spotify_track_id,
                rating=rating
            ))

        db.session.commit()
        return jsonify({
            "message": "Rating updated",
            "playlist": playlist.name,
            "track": track.name,
            "rating": rating
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Rating failed", "details": str(e)}), 500


def handle_favorite_operation(data):
    """Manage favorites using natural identifiers"""
    user_id = get_jwt_identity()
    if isinstance(user_id, dict):
        user_id = user_id.get("id")
    else:
        user_id = user_id
    item_type = data.get("type")

    if not item_type or item_type not in ["track", "album"]:
        return jsonify({"error": "Invalid item type"}), 400

    try:
        if item_type == "track":
            playlist_name = data.get("playlist_name")
            track_name = data.get("track_name")

            if not all([playlist_name, track_name]):
                return jsonify({"error": "Missing playlist/track names"}), 400

            # Get track from playlist
            playlist = Playlist.query.filter_by(
                user_id=user_id,
                name=playlist_name
            ).first()

            if not playlist:
                return jsonify({"error": "Playlist not found"}), 404

            track = Track.query.filter_by(
                playlist_id=playlist.id,
                name=track_name
            ).first()

            if not track:
                return jsonify({"error": "Track not found"}), 404

            spotify_id = track.spotify_track_id
        else:
            # For albums, still use direct Spotify ID
            spotify_id = data.get("spotify_id")
            if not spotify_id:
                return jsonify({"error": "Missing Spotify ID for album"}), 400

        if request.method == "POST":
            if Favorite.query.filter_by(
                    user_id=user_id,
                    spotify_id=spotify_id
            ).first():
                return jsonify({"error": "Already favorited"}), 400

            db.session.add(Favorite(
                user_id=user_id,
                spotify_id=spotify_id,
                type=item_type
            ))
            message = "Added to favorites"
            status = 201
        else:
            favorite = Favorite.query.filter_by(
                user_id=user_id,
                spotify_id=spotify_id
            ).first()

            if not favorite:
                return jsonify({"error": "Favorite not found"}), 404

            db.session.delete(favorite)
            message = "Removed from favorites"
            status = 200

        db.session.commit()
        return jsonify({"message": message, "item": spotify_id}), status

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Favorite operation failed", "details": str(e)}), 500


def update_playlist_details(playlist_id, data):
    """Update playlist metadata"""
    user_id = get_jwt_identity()
    if isinstance(user_id, dict):
        user_id = user_id.get("id")
    else:
        user_id = user_id
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=user_id).first()

    if not playlist:
        return jsonify({"error": "Playlist not found"}), 404

    if name := data.get("name"):
        playlist.name = name
    if description := data.get("description"):
        playlist.description = description

    # Sync with Spotify
    if playlist.spotify_id:
        try:
            sp.playlist_change_details(
                playlist_id=playlist.spotify_id,
                name=playlist.name,
                description=playlist.description
            )
        except Exception as e:
            return jsonify({"error": "Spotify update failed", "details": str(e)}), 500

    db.session.commit()
    return jsonify({"message": "Playlist updated", "playlist": playlist_schema.dump(playlist)}), 200


# services.py - Add these new functions

def add_comment_to_track(user_id, playlist_name, track_name, comment):
    """Add a comment to a track using natural identifiers"""
    try:
        # Get playlist with ownership check
        playlist = Playlist.query.filter_by(
            user_id=user_id,
            name=playlist_name
        ).first()

        if not playlist:
            return {"error": "Playlist not found"}, 404

        # Find track with case-insensitive search
        track = Track.query.filter(
            Track.playlist_id == playlist.id,
            Track.name.ilike(track_name)
        ).first()

        if not track:
            return {"error": "Track not found in playlist"}, 404

        # Create and save comment
        new_comment = TrackComment(
            user_id=user_id,
            track_id=track.id,
            comment=comment
        )
        db.session.add(new_comment)
        db.session.commit()

        return {"message": "Comment added", "comment": track_comment_schema.dump(new_comment)}, 201

    except Exception as e:
        db.session.rollback()
        return {"error": "Failed to add comment", "details": str(e)}, 500






def get_track_comments(user_id, playlist_name, track_name):
    """Retrieve comments for a specific track"""
    try:
        # Verify playlist ownership
        playlist = Playlist.query.filter_by(
            user_id=user_id,
            name=playlist_name
        ).first()

        if not playlist:
            return {"error": "Playlist not found"}, 404

        # Find track with case-insensitive search
        track = Track.query.filter(
            Track.playlist_id == playlist.id,
            Track.name.ilike(track_name)
        ).first()

        if not track:
            return {"error": "Track not found in playlist"}, 404

        # Get all comments for this track
        comments = TrackComment.query.filter_by(track_id=track.id).all()
        return {"comments": track_comments_schema.dump(comments)}, 200

    except Exception as e:
        return {"error": "Failed to retrieve comments", "details": str(e)}, 500


def generate_share_link(user_id, playlist_name):
    """Generate Spotify share link for a playlist"""
    try:
        # Get playlist with ownership check
        playlist = Playlist.query.filter_by(
            user_id=user_id,
            name=playlist_name
        ).first()

        if not playlist:
            return {"error": "Playlist not found"}, 404

        if not playlist.spotify_id:
            return {"error": "Playlist not synced with Spotify"}, 400

        return {
                   "share_url": f"https://open.spotify.com/playlist/{playlist.spotify_id}",
                   "playlist_name": playlist.name,
                   "owner": playlist.user.username
               }, 200

    except Exception as e:
        return {"error": str(e)}, 500









# ------ Time Capsule Playlists ------
def generate_time_capsule_playlist():
    try:
        time_ranges = ['short_term', 'medium_term', 'long_term']
        all_tracks = []

        for tr in time_ranges:
            top_tracks = sp.current_user_top_tracks(
                limit=20,
                time_range=tr
            )
            all_tracks.extend([item['uri'] for item in top_tracks['items']])

        # Create playlist
        playlist = sp.user_playlist_create(
            user=sp.me()['id'],
            name=f"Time Capsule {datetime.now().year}",
            public=False
        )

        # Add unique tracks
        sp.playlist_add_items(playlist['id'], list(set(all_tracks)))

        return jsonify({
            "playlist_url": playlist['external_urls']['spotify']
        }), 201
    except SpotifyException as e:
        return {"error": str(e)}, 500











# ----Cultural Time Machine
def generate_cultural_time_machine(year):
    try:
        user_id = get_jwt_identity()
        if isinstance(user_id, dict):
            user_id = user_id.get("id")
        else:
            user_id = user_id
        if year < 1900 or year > datetime.now().year:
            return {"error": "Invalid year"}, 400

        # Get top tracks for the year
        results = sp.search(
            q=f"year:{year}",
            type='track',
            limit=50,
            market='US'
        )
        tracks = results['tracks']['items']
        if not tracks:
            return {"error": "No tracks found for this year"}, 404

        # Create playlist
        playlist_name = f"{year} Time Machine"
        existing = Playlist.query.filter_by(user_id=user_id, name=playlist_name).first()
        spotify_user_id = sp.current_user()['id']

        if existing:
            sp.playlist_replace_items(existing.spotify_id, [])
            sp.playlist_add_items(existing.spotify_id, [t['uri'] for t in tracks])
            return {"message": "Playlist updated", "playlist_id": existing.spotify_id}, 200
        else:
            playlist = sp.user_playlist_create(
                spotify_user_id,
                name=playlist_name,
                public=False,
                description=f"Top tracks from {year}"
            )
            sp.playlist_add_items(playlist['id'], [t['uri'] for t in tracks])
            new_playlist = Playlist(
                user_id=user_id,
                name=playlist_name,
                spotify_id=playlist['id']
            )
            db.session.add(new_playlist)
            db.session.commit()
            return {"message": "Playlist created", "playlist_id": playlist['id']}, 201

    except SpotifyException as e:
        return {"error": f"Spotify API error: {str(e)}"}, e.http_status
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": "Failed to generate playlist"}, 500


# Add these functions to services.py
def generate_text_based_playlist(data):
    """Create playlist from text description"""
    try:
        user_id = get_jwt_identity()
        if isinstance(user_id, dict):
            user_id = user_id.get("id")
        else:
            user_id = user_id
        description = data.get("description")

        if not description:
            return {"error": "Description is required"}, 400

        # Search Spotify for relevant tracks
        results = sp.search(q=description, type='track', limit=20)
        if not results['tracks']['items']:
            return {"error": "No tracks found matching description"}, 404

        track_uris = [track['uri'] for track in results['tracks']['items']]

        # Create Spotify playlist
        spotify_user = sp.current_user()
        playlist = sp.user_playlist_create(
            user=spotify_user['id'],
            name=f"Generated: {description[:50]}",
            public=False,
            description=f"Created from description: {description}"
        )

        # Add tracks to playlist
        sp.playlist_add_items(playlist['id'], track_uris)

        # Save to local database
        new_playlist = Playlist(
            user_id=user_id,
            name=playlist['name'],
            spotify_id=playlist['id']
        )
        db.session.add(new_playlist)
        db.session.commit()

        return {"message": "Playlist created", "playlist": playlist_schema.dump(new_playlist)}, 201

    except SpotifyException as e:
        return {"error": f"Spotify API error: {str(e)}"}, e.http_status
    except Exception as e:
        logger.error(f"Text playlist error: {str(e)}")
        return {"error": "Failed to create playlist"}, 500


def merge_playlists(data):
    """Merge two playlists into one"""
    try:
        user_id = get_jwt_identity()
        if isinstance(user_id, dict):
            user_id = user_id.get("id")
        else:
            user_id = user_id
        playlist1_id = data.get("playlist1_id")
        playlist2_id = data.get("playlist2_id")

        if not playlist1_id or not playlist2_id:
            return {"error": "Both playlist IDs are required"}, 400

        # Verify ownership and get Spotify IDs
        playlist1 = Playlist.query.filter_by(user_id=user_id, id=playlist1_id).first()
        playlist2 = Playlist.query.filter_by(user_id=user_id, id=playlist2_id).first()

        if not playlist1 or not playlist2:
            return {"error": "One or both playlists not found"}, 404

        if not playlist1.spotify_id or not playlist2.spotify_id:
            return {"error": "Both playlists must have Spotify IDs"}, 400

        # Get all tracks from both playlists
        def get_all_tracks(playlist_id):
            tracks = []
            results = sp.playlist_tracks(playlist_id)
            tracks.extend(results['items'])
            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])
            return list(set([item['track']['uri'] for item in tracks]))

        tracks1 = get_all_tracks(playlist1.spotify_id)
        tracks2 = get_all_tracks(playlist2.spotify_id)
        combined = list(set(tracks1 + tracks2))

        # Create new playlist
        spotify_user = sp.current_user()
        new_playlist = sp.user_playlist_create(
            user=spotify_user['id'],
            name=f"Merge: {playlist1.name} + {playlist2.name}",
            public=False,
            description=f"Combined playlist from {playlist1.name} and {playlist2.name}"
        )

        # Add tracks in batches
        for i in range(0, len(combined), 100):
            sp.playlist_add_items(new_playlist['id'], combined[i:i + 100])

        # Save to database
        merged_playlist = Playlist(
            user_id=user_id,
            name=new_playlist['name'],
            spotify_id=new_playlist['id']
        )
        db.session.add(merged_playlist)
        db.session.commit()

        return {"message": "Playlists merged", "playlist": playlist_schema.dump(merged_playlist)}, 201

    except SpotifyException as e:
        return {"error": f"Spotify API error: {str(e)}"}, e.http_status
    except Exception as e:
        logger.error(f"Merge error: {str(e)}")
        return {"error": "Failed to merge playlists"}, 500


def get_user_comments():
    """Retrieve all comments made by the authenticated user"""
    try:
        user_id = get_jwt_identity()
        if isinstance(user_id, dict):
            user_id = user_id.get("id")
        else:
            user_id = user_id
        # Get comments ordered by creation date (newest first)
        comments = TrackComment.query.filter_by(user_id=user_id) \
            .order_by(TrackComment.created_at.desc()).all()

        return jsonify({
            "comments": track_comments_schema.dump(comments)
        }), 200

    except Exception as e:
        logger.error(f"Failed to fetch user comments: {str(e)}")
        return jsonify({"error": "Failed to retrieve comments", "details": str(e)}), 500