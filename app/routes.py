from flask import Blueprint, request, jsonify, redirect
from app.auth import register_user, login_user, initiate_spotify_login, handle_spotify_callback
from app.services import (
    create_playlist,
    get_playlists,
    add_track_to_playlist,
    remove_track_from_playlist,
    get_tracks_from_playlist, update_playlist_details,
    handle_song_feedback,
    handle_favorite_operation,
)
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.spotify_services import (
    fetch_genres, search_track_by_artist, get_track_info,
    get_album_info, fetch_trending_tracks, fetch_featured_playlists
)
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
@jwt_required()  # ADD THIS DECORATOR
def get_playlists_route():
    try:
        return get_playlists()
    except Exception as e:
        return jsonify({"error": "Failed to fetch playlists", "details": str(e)}), 500


@api_bp.route("/playlist/<int:playlist_id>/add-track", methods=["POST"])
@jwt_required()
def add_track(playlist_id):
    try:
        data = request.get_json()
        return add_track_to_playlist(playlist_id, data)  # ✅ Now it matches the function signature
    except Exception as e:
        return jsonify({"error": "Failed to add track", "details": str(e)}), 500


@api_bp.route("/music/remove", methods=["DELETE"])
@jwt_required()
def remove_track():
    try:
        data = request.get_json()
        return remove_track_from_playlist(data)
    except Exception as e:
        return jsonify({"error": "Removal failed", "details": str(e)}), 500


@api_bp.route("/playlist/<int:playlist_id>/tracks", methods=["GET"])
def get_tracks(playlist_id):
    try:
        return get_tracks_from_playlist(playlist_id)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve tracks", "details": str(e)}), 500

# ✅ Fetch Available Genres
@api_bp.route("/spotify/genres", methods=["GET"])
def get_genres():
    return fetch_genres()

# ✅ Search Track by Artist
@api_bp.route("/spotify/search/<artist_name>", methods=["GET"])
def search_tracks(artist_name):
    return search_track_by_artist(artist_name)

# ✅ Get Detailed Track Info
@api_bp.route("/spotify/track/<track_id>", methods=["GET"])
def track_info(track_id):
    return get_track_info(track_id)

# ✅ Get Album Info
@api_bp.route("/spotify/album/<album_id>", methods=["GET"])
def album_info(album_id):
    return get_album_info(album_id)

# ✅ Fetch Trending Tracks
@api_bp.route("/spotify/trending", methods=["GET"])
def trending_tracks():
    return fetch_trending_tracks()

# ✅ Spotify OAuth Login
@api_bp.route("/spotify/login", methods=["GET"])
def spotify_login():
    """
    1️⃣ User must first be logged in with traditional credentials.
    2️⃣ API receives `user_id` and redirects to Spotify OAuth.
    """
    try:
        user_id = request.args.get("user_id")
        response, status_code = initiate_spotify_login(user_id)
        if status_code == 302:
            return redirect(response["redirect_url"])
        return jsonify(response), status_code

    except Exception as e:
        return jsonify({"error": "Spotify login failed", "details": str(e)}), 500


# ✅ Spotify OAuth Callback
@api_bp.route("/callback", methods=["GET"])
def spotify_callback():
    """
    1️⃣ Fetch Spotify token using authorization code.
    2️⃣ Retrieve Spotify user profile.
    3️⃣ Link to existing user OR create a new user.
    4️⃣ Return JWT token for authenticated access.
    """
    try:
        auth_code = request.args.get("code")
        response, status_code = handle_spotify_callback(auth_code)
        return jsonify(response), status_code  # ✅ Ensures JSON response
    except Exception as e:
        return jsonify({"error": "Spotify authentication failed", "details": str(e)}), 500


# ✅ Fetch Featured Playlists Endpoint
@api_bp.route("/spotify/featured-playlists", methods=["GET"])
def featured_playlists():
    try:
        limit = request.args.get("limit", default=10, type=int)
        offset = request.args.get("offset", default=0, type=int)
        country = request.args.get("country", default="US", type=str)  # Default: US

        return fetch_featured_playlists(limit=limit, offset=offset, country=country)

    except Exception as e:
        print(f"❌ Route Error: {str(e)}")
        return jsonify({"error": "Failed to fetch featured playlists", "details": str(e)}), 500


# Add to routes.py
@api_bp.route("/feedback", methods=["POST"])
@jwt_required()
def submit_feedback():
    try:
        data = request.get_json()
        return handle_song_feedback(data)
    except Exception as e:
        return jsonify({"error": "Feedback failed", "details": str(e)}), 500

@api_bp.route("/music/favorite", methods=["POST", "DELETE"])
@jwt_required()
def manage_favorite():
    try:
        data = request.get_json()
        return handle_favorite_operation(data)
    except Exception as e:
        return jsonify({"error": "Favorite operation failed", "details": str(e)}), 500




@api_bp.route("/music/rate", methods=["POST"])
@jwt_required()
def rate_track():
    try:
        data = request.get_json()
        return handle_song_feedback(data)
    except Exception as e:
        return jsonify({"error": "Rating failed", "details": str(e)}), 500

@api_bp.route("/playlist/update/<int:playlist_id>", methods=["PUT"])
@jwt_required()
def update_playlist(playlist_id):
    try:
        data = request.get_json()
        return update_playlist_details(playlist_id, data)
    except Exception as e:
        return jsonify({"error": "Update failed", "details": str(e)}), 500