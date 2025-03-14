
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Playlist, Track, Favorite, UserRating, TrackComment, User
from app.serializers import playlists_schema, track_schema, playlist_schema, track_comment_schema, track_comments_schema
from app.extensions import sp, sp_oauth  # Changed import source
from datetime import datetime

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
        name = data.get("name")
        description = data.get("description", "")
        is_public = data.get("public", False)
        is_collaborative = data.get("collaborative", False)

        if not user_id or not name:
            return jsonify({"error": "Missing playlist name"}), 400

        # ✅ Fetch Spotify User ID
        spotify_user = sp.current_user()
        spotify_user_id = spotify_user["id"]

        # ✅ Create Playlist on Spotify
        spotify_playlist = sp.user_playlist_create(
            user=spotify_user_id,
            name=name,
            public=is_public,
            collaborative=is_collaborative,
            description=description
        )

        spotify_playlist_id = spotify_playlist["id"]
        spotify_playlist_url = spotify_playlist["external_urls"]["spotify"]

        # ✅ Store Playlist in Local Database
        new_playlist = Playlist(
            user_id=user_id,
            name=name,
            description=description,
            spotify_id=spotify_playlist_id  # ✅ Store Spotify Playlist ID
        )
        db.session.add(new_playlist)
        db.session.commit()

        return jsonify({
            "message": "Playlist created successfully!",
            "playlist": {
                "id": new_playlist.id,
                "name": new_playlist.name,
                "description": new_playlist.description,
                "user_id": new_playlist.user_id,
                "spotify_playlist_id": spotify_playlist_id,
                "spotify_url": spotify_playlist_url
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create playlist", "details": str(e)}), 500

@jwt_required()
def get_playlists():
    """Retrieve all playlists for the authenticated user."""
    user_id = get_jwt_identity()
    playlists = Playlist.query.filter_by(user_id=user_id).all()

    if not playlists:
        return jsonify({"message": "No playlists found"}), 200

    return jsonify(playlists_schema.dump(playlists)), 200


@jwt_required()
def add_track_to_playlist(playlist_id, data):
    """Add a track to a specific playlist (Both Local & Spotify)."""
    try:
        user_id = get_jwt_identity()
        playlist = Playlist.query.filter_by(id=playlist_id, user_id=user_id).first()

        if not playlist:
            return jsonify({"error": "Playlist not found"}), 404

        if not playlist.spotify_id:
            return jsonify({"error": "This playlist does not have a linked Spotify ID"}), 400

        # ✅ Validate incoming data
        track_name = data.get("name", "").strip()
        artist_name = data.get("artist", "").strip()
        album_name = data.get("album", "").strip() if data.get("album") else None

        if not track_name or not artist_name:
            return jsonify({"error": "Invalid track name or artist"}), 400

        # ✅ Search Track on Spotify
        search_query = f"track:{track_name} artist:{artist_name}"
        search_result = sp.search(q=search_query, type="track", limit=1)

        if not search_result["tracks"]["items"]:
            return jsonify({"error": "Track not found on Spotify"}), 404

        spotify_track_uri = search_result["tracks"]["items"][0]["uri"]
        # Extract Spotify Track ID from URI (NEW)
        spotify_track_id = spotify_track_uri.split(":")[-1]  # Get last part of "spotify:track:abc123"
        # ✅ Add Track to Spotify Playlist
        sp.playlist_add_items(playlist_id=playlist.spotify_id, items=[spotify_track_uri])

        # ✅ Save to Local Database
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


@jwt_required()
def get_tracks_from_playlist(playlist_id):
    """Retrieve all tracks from a playlist."""
    user_id = get_jwt_identity()
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=user_id).first()

    if not playlist:
        return jsonify({"error": "Playlist not found"}), 404

    tracks = Track.query.filter_by(playlist_id=playlist.id).all()

    if not tracks:
        return jsonify({"message": "No tracks found in this playlist"}), 200

    return jsonify(track_schema.dump(tracks)), 200


# In services.py
def handle_song_feedback(data):
    """Handle song ratings using playlist/track names"""
    user_id = get_jwt_identity()
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


