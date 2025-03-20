from datetime import datetime
import spotipy

from flask import jsonify, request

from app.extensions import sp, sp_oauth  # Changed import source
# ✅ Load environment variables




# ✅ Debugging: Verify OAuth Initialization
if not sp_oauth:
    print("❌ ERROR: Spotify OAuth is NOT initialized correctly.")
else:
    print("✅ Spotify OAuth initialized successfully.")




# ✅ Set Album ID for Trending Tracks
PLAYLIST_ID = "2PvZKuj3e0FPqDHNUCZCSv"  # Replace with your desired album
# print(sp.playlist(PLAYLIST_ID))  # Check if this returns valid data



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



def advanced_track_search(params):
    """Advanced track search with multiple filters"""
    try:
        # Parameter extraction
        year = params.get('year')
        genre = params.get('genre')
        artist = params.get('artist')
        limit = params.get('limit', 10)
        errors = []

        # Validation
        if year:
            try:
                year = int(year)
                if year < 1900 or year > datetime.now().year:
                    errors.append(f"Year must be between 1900-{datetime.now().year}")
            except ValueError:
                errors.append("Invalid year format")

        try:
            limit = int(limit)
            if not (1 <= limit <= 50):
                errors.append("Limit must be 1-50")
        except ValueError:
            errors.append("Invalid limit value")

        if errors:
            return jsonify({"errors": errors}), 400

        # Build query
        query_parts = []
        if year: query_parts.append(f"year:{year}")
        if genre: query_parts.append(f"genre:{genre}")
        if artist: query_parts.append(f"artist:{artist}")

        if not query_parts:
            return jsonify({"error": "At least one filter required"}), 400

        # Spotify API call
        results = sp.search(q=' '.join(query_parts), type='track', limit=limit)
        tracks = [{
            'name': track['name'],
            'artists': [a['name'] for a in track['artists']],
            'album': track['album']['name'],
            'release_date': track['album']['release_date'],
            'id': track['id'],
            'uri': track['uri'],
            'preview_url': track.get('preview_url'),
            'popularity': track['popularity']
        } for track in results['tracks']['items']]

        return jsonify({
            'tracks': tracks,
            'total': results['tracks']['total']
        }), 200

    except Exception as e:
        return jsonify({"error": "Search failed", "details": str(e)}), 500
