from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Playlist, Track
from app.serializers import playlists_schema, playlist_schema, track_schema, tracks_schema


def create_playlist(data):
    """Create a playlist for the logged-in user."""
    try:
        user_id = get_jwt_identity()  # ✅ Extract user ID from JWT token
        name = data.get("name")
        description = data.get("description", "")

        if not user_id or not name:
            return jsonify({"error": "Missing playlist name"}), 400  # ✅ "user_id" is now always available

        new_playlist = Playlist(user_id=user_id, name=name, description=description)
        db.session.add(new_playlist)
        db.session.commit()

        return jsonify({
            "message": "Playlist created successfully!",
            "playlist": {
                "id": new_playlist.id,
                "name": new_playlist.name,
                "description": new_playlist.description,
                "user_id": new_playlist.user_id
            }
        }), 201
    except Exception as e:
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
def add_track_to_playlist(playlist_id):
    """Add a track to a specific playlist."""
    user_id = get_jwt_identity()
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=user_id).first()

    if not playlist:
        return jsonify({"error": "Playlist not found"}), 404

    data = request.get_json()
    new_track = Track(
        name=data["name"],
        artist=data["artist"],
        album=data.get("album"),
        playlist_id=playlist.id
    )

    db.session.add(new_track)
    db.session.commit()

    return jsonify({"message": "Track added!", "track": track_schema.dump(new_track)}), 201


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
