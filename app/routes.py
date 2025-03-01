from flask import Blueprint, request, jsonify
from app.auth import register_user, login_user
from app.services import (
    create_playlist,
    get_playlists,
    add_track_to_playlist,
    remove_track_from_playlist,
    get_tracks_from_playlist
)
from flask_jwt_extended import jwt_required
# Create API Blueprint
api_bp = Blueprint("api", __name__)

# ✅ User Authentication Routes
@api_bp.route("/register", methods=["POST"])
def register():
    try:
        return register_user()  # ✅ Correct function call
    except Exception as e:
        return jsonify({"error": "Failed to register user", "details": str(e)}), 500


@api_bp.route("/login", methods=["POST"])
def login():
    try:
        return login_user()  # ✅ Correct function call
    except Exception as e:
        return jsonify({"error": "Login failed", "details": str(e)}), 500

@api_bp.route("/playlist", methods=["POST"])
@jwt_required()  # ✅ Requires JWT authentication
def create_playlist_route():
    try:
        data = request.get_json()  # ✅ Get JSON data from request
        return create_playlist(data)  # ✅ Now correctly passes `data`
    except Exception as e:
        return jsonify({"error": "Failed to create playlist", "details": str(e)}), 500



@api_bp.route("/user/playlists", methods=["GET"])
def get_playlists_route():
    try:
        return get_playlists()
    except Exception as e:
        return jsonify({"error": "Failed to fetch playlists", "details": str(e)}), 500


# ✅ Track Routes
@api_bp.route("/playlist/<int:playlist_id>/add-track", methods=["POST"])
def add_track(playlist_id):
    try:
        data = request.get_json()
        return add_track_to_playlist(playlist_id, data)  # ✅ Ensure data is passed
    except Exception as e:
        return jsonify({"error": "Failed to add track", "details": str(e)}), 500


@api_bp.route("/playlist/<int:playlist_id>/remove-track/<int:track_id>", methods=["DELETE"])
def remove_track(playlist_id, track_id):
    try:
        return remove_track_from_playlist(playlist_id, track_id)
    except Exception as e:
        return jsonify({"error": "Failed to remove track", "details": str(e)}), 500


@api_bp.route("/playlist/<int:playlist_id>/tracks", methods=["GET"])
def get_tracks(playlist_id):
    try:
        return get_tracks_from_playlist(playlist_id)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve tracks", "details": str(e)}), 500
