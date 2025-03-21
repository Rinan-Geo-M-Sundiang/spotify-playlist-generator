
from spotipy.oauth2 import SpotifyOAuth
import spotipy
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv



load_dotenv()

# Configure retry strategy with backoff
retry_strategy = Retry(
    total=3,  # Total retry attempts
    backoff_factor=1,  # Wait 1s, 2s, 4s between retries
    status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
    allowed_methods=["GET", "POST", "PUT", "DELETE"]  # Retry on all HTTP methods
)

# Create custom HTTP adapter with retry logic
adapter = HTTPAdapter(max_retries=retry_strategy)

# Configure session with timeout and retry
session = requests.Session()
session.mount("https://", adapter)
session.mount("http://", adapter)

#  Initialize Spotify OAuth (Ensures Token Refresh & Correct Scope)
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri="http://localhost:5000/callback",  #  Matches your redirect route
    scope = "playlist-read-collaborative user-read-private playlist-modify-public playlist-modify-private user-library-read user-library-modify playlist-read-private user-top-read",
    cache_path=".spotifycache",  # Added cache path for token persistence
    requests_session=session # Use our custom session
)

# Initialize Spotipy client with timeout settings
sp = spotipy.Spotify(
    auth_manager=sp_oauth,
    requests_timeout=(3.05, 10),  # Connect timeout: 3.05s, Read timeout: 10s
    requests_session=session,
    retries=3  # Additional layer of retries
)