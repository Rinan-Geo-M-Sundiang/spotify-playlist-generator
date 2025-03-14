from spotipy.oauth2 import SpotifyOAuth
import spotipy
import os
from dotenv import load_dotenv

load_dotenv()
# ✅ Initialize Spotify OAuth (Ensures Token Refresh & Correct Scope)
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri="http://localhost:5000/callback",  # ✅ Matches your redirect route
    scope="playlist-read-collaborative user-read-private playlist-modify-public playlist-modify-private "
          "user-library-read user-library-modify playlist-read-private ",
    cache_path=".spotifycache"  # Added cache path for token persistence
)

# ✅ Create Spotipy Client Using OAuth
sp = spotipy.Spotify(auth_manager=sp_oauth)