import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from flask import jsonify, request
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
import datetime

# ✅ Load environment variables
load_dotenv()
# ✅ Initialize Spotify OAuth (Ensures Token Refresh & Correct Scope)
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri="http://localhost:5000/callback",  # ✅ Matches your redirect route
    scope="user-read-private playlist-read-private playlist-modify-public playlist-modify-private user-top-read"
)

# ✅ Create Spotipy Client Using OAuth
sp = spotipy.Spotify(auth_manager=sp_oauth)

# ✅ Debugging: Verify OAuth Initialization
if not sp_oauth:
    print("❌ ERROR: Spotify OAuth is NOT initialized correctly.")
else:
    print("✅ Spotify OAuth initialized successfully.")


# ✅ Set Album ID for Trending Tracks
PLAYLIST_ID = "2PvZKuj3e0FPqDHNUCZCSv"  # Replace with your desired album
# print(sp.playlist(PLAYLIST_ID))  # Check if this returns valid data


def fetch_genres():
    """Fetch available genres from Spotify with proper token handling"""
    try:
        # ✅ Get FRESH token with forced refresh check
        token_info = sp_oauth.get_access_token(as_dict=False)
        if not token_info:
            return jsonify({"error": "Login required at /spotify/login"}), 401

        # ✅ DEBUG: Print token status
        print(f"🔥 Using token: {token_info[:15]}... (expires in {sp_oauth._get_expires_at() - time.time()}s)")

        # ✅ Create NEW client with fresh token
        authorized_sp = spotipy.Spotify(auth=token_info)
        genres = authorized_sp.recommendation_genre_seeds()

        return jsonify({"genres": genres["genres"]}), 200

    except spotipy.SpotifyException as e:
        return jsonify({
            "error": "Spotify API Error",
            "solution": "Reauthenticate at /spotify/login",
            "details": str(e)
        }), e.http_status

def search_track_by_artist(artist_name):
    """Search for a track by artist name."""
    try:
        results = sp.search(q=f"artist:{artist_name}", type="track", limit=10)
        tracks = [
            {"name": track["name"], "artist": track["artists"][0]["name"], "album": track["album"]["name"]}
            for track in results["tracks"]["items"]
        ]
        return jsonify({"tracks": tracks}), 200
    except Exception as e:
        return jsonify({"error": "Failed to search tracks", "details": str(e)}), 500

def get_track_info(track_id):
    """Fetch detailed track information by track ID."""
    try:
        track = sp.track(track_id)
        return jsonify({
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "album": track["album"]["name"],
            "release_date": track["album"]["release_date"]
        }), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch track info", "details": str(e)}), 500

def get_album_info(album_id):
    """Fetch information about an album including tracks and release year."""
    try:
        album = sp.album(album_id)
        tracks = [{"name": track["name"], "track_number": track["track_number"]} for track in album["tracks"]["items"]]
        return jsonify({
            "album_name": album["name"],
            "artist": album["artists"][0]["name"],
            "release_date": album["release_date"],
            "cover_art": album["images"][0]["url"],
            "tracks": tracks
        }), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch album info", "details": str(e)}), 500


def fetch_trending_tracks():
    """Fetch top 10 tracks from the Global Top 50 playlist."""
    try:
        print(f"🔍 Checking if playlist ID {PLAYLIST_ID} is valid...")

        # ✅ Check if the playlist exists before fetching tracks
        playlist_info = sp.playlist(PLAYLIST_ID)
        if not playlist_info:
            print("❌ Playlist not found. Double-check the playlist ID.")
            return jsonify({"error": "Playlist not found"}), 404

        print(f"✅ Playlist '{playlist_info['name']}' found!")

        # ✅ Fetch playlist tracks (Limit to 10, No `market` filter)
        playlist_tracks = sp.playlist_tracks(PLAYLIST_ID, limit=10)

        print("📥 Spotify API Response (Playlist Tracks):", playlist_tracks)  # Debugging

        # ✅ Extract track data
        tracks = [
            {
                "name": track["track"]["name"],
                "artist": track["track"]["artists"][0]["name"],
                "album": track["track"]["album"]["name"]
            }
            for track in playlist_tracks["items"] if track["track"]
        ]

        print("✅ Trending tracks fetched successfully!")  # Debugging
        return jsonify({"trending_tracks": tracks}), 200

    except spotipy.exceptions.SpotifyException as e:
        print(f"❌ Spotify API Error: {str(e)}")  # Debugging
        return jsonify({"error": "Failed to fetch trending tracks from Spotify", "details": str(e)}), e.http_status

    except Exception as e:
        print(f"❌ General Error fetching trending tracks: {str(e)}")  # Debugging
        return jsonify({"error": "Unexpected error occurred", "details": str(e)}), 500


# ✅ Fetch Featured Playlists
def fetch_featured_playlists(limit=10, offset=0, country="US"):
    """Fetch Spotify's featured playlists."""
    try:
        print(f"🔍 Fetching Featured Playlists for Country: {country}...")

        # ✅ Ensure Access Token is Valid (Auto-refresh if needed)
        token_info = sp_oauth.get_cached_token()
        if not token_info:
            print("❌ No valid access token. User must reauthenticate.")
            return jsonify({"error": "Authentication required"}), 401

        print("✅ Token is valid. Proceeding with API request.")

        # ✅ Correct API Call (Avoid `_get()` Deprecated Calls)
        response = sp.featured_playlists(
            limit=limit,
            offset=offset,
            country=country
        )

        # ✅ Debugging: Print Raw API Response
        print("📥 Raw API Response:", response)

        # ✅ Extract Playlist Details
        playlists = response.get("playlists", {}).get("items", [])

        featured_playlists = [
            {
                "name": playlist["name"],
                "description": playlist["description"],
                "url": playlist["external_urls"]["spotify"],
                "image": playlist["images"][0]["url"] if playlist["images"] else None
            }
            for playlist in playlists
        ]

        print("✅ Successfully fetched featured playlists!")  # Debugging
        return jsonify({"featured_playlists": featured_playlists}), 200

    except spotipy.exceptions.SpotifyException as e:
        print(f"❌ Spotify API Error: {str(e)}")  # Debugging
        return jsonify({"error": "Failed to fetch featured playlists", "details": str(e)}), e.http_status

    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")  # Debugging
        return jsonify({"error": "Unexpected error occurred", "details": str(e)}), 500