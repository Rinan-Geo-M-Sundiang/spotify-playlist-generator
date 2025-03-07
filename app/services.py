import spotipy
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Playlist, Track
from app.serializers import playlists_schema, playlist_schema, track_schema, tracks_schema
from app.spotify_services import sp  # ✅ Ensure `sp` is using SpotifyOAuth authentication

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

        # ✅ Add Track to Spotify Playlist
        sp.playlist_add_items(playlist_id=playlist.spotify_id, items=[spotify_track_uri])

        # ✅ Save to Local Database
        new_track = Track(
            name=track_name,
            artist=artist_name,
            album=album_name if album_name else None,
            playlist_id=playlist.id
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



@jwt_required()
def remove_track_from_playlist(playlist_id, track_id):
    """Remove a track from a playlist."""
    user_id = get_jwt_identity()
    track = Track.query.filter_by(id=track_id, playlist_id=playlist_id).first()

    if not track:
        return jsonify({"error": "Track not found"}), 404

    db.session.delete(track)
    db.session.commit()

    return jsonify({"message": "Track removed!"}), 200


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

    return jsonify(tracks_schema.dump(tracks)), 200
