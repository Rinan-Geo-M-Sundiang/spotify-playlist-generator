
import bcrypt
from flask import request, jsonify, session
from flask_jwt_extended import create_access_token
from app import db
from app.models import User
from app.serializers import user_schema
from app.extensions import sp, sp_oauth  # Changed import source

def register_user():
    """Register a new user and return a JWT token."""
    try:
        data = request.get_json()

        #  Validate input
        if not data or "username" not in data or "password" not in data:
            return jsonify({"error": "Missing username or password"}), 400

        #  Check if user already exists
        existing_user = User.query.filter_by(username=data["username"]).first()
        if existing_user:
            return jsonify({"error": "Username already exists"}), 400

        #  Hash the password
        hashed_pw = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        #  Create and save user
        new_user = User(username=data["username"], password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        #  Generate JWT token
        token = create_access_token(identity=new_user.id)

        response = {
            "message": "User registered successfully!",
            "access_token": token,
            "user": user_schema.dump(new_user)
        }

        return jsonify(response), 201
    except Exception as e:
        return jsonify({"error": "Failed to register user", "details": str(e)}), 500



#  Traditional User Login
def login_user():
    """Authenticate user with username/password and return JWT token."""
    try:
        data = request.get_json()

        #  Validate Input
        if not data or "username" not in data or "password" not in data:
            return {"error": "Missing username or password"}, 400

        #  Fetch user from database
        user = User.query.filter_by(username=data["username"]).first()
        if not user:
            return {"error": "Invalid username or password"}, 401

        #  Validate Password
        if not bcrypt.checkpw(data["password"].encode('utf-8'), user.password_hash.encode('utf-8')):
            return {"error": "Invalid username or password"}, 401

        #  Generate JWT Token
        token = create_access_token(identity=str(user.id))

        response = {
            "message": "Login successful",
            "access_token": token,
            "user": user_schema.dump(user),
            "spotify_login": f"http://127.0.0.1:5000/spotify/login?user_id={user.id}"  #  Optional Spotify Login
        }

        return response, 200

    except Exception as e:
        print(f" Error in login: {str(e)}")  # Debugging
        return {"error": "Failed to login", "details": str(e)}, 500


#  Initiate Spotify OAuth Login
def initiate_spotify_login(user_id):
    """Redirect user to Spotify OAuth for authentication."""
    try:
        if not user_id:
            return {"error": "User ID required"}, 400

        session["pending_user_id"] = user_id  # Store User ID in session
        auth_url = sp_oauth.get_authorize_url()
        print(f" Redirecting to Spotify login: {auth_url}")
        return {"redirect_url": auth_url}, 302

    except Exception as e:
        print(f" Spotify Login Error: {str(e)}")
        return {"error": "Spotify login failed", "details": str(e)}, 500


def handle_spotify_callback(auth_code):
    """Process Spotify authentication callback, link account to user, and return JWT."""
    try:
        if not auth_code:
            return {"error": "Missing authorization code"}, 400

        #  FIX 1: Get token as dictionary with ALL required parameters
        token_info = sp_oauth.get_access_token(
            code=auth_code,
            as_dict=True,
            check_cache=False
        )

        #  FIX 2: Validate token structure
        if not isinstance(token_info, dict) or "access_token" not in token_info:
            print(f" Invalid token format: {type(token_info)} - {token_info}")
            return {"error": "Invalid Spotify token format"}, 500

        session["spotify_token_info"] = token_info
        sp.set_auth(token_info["access_token"])

        #  Fetch Spotify User Profile
        spotify_user = sp.current_user()
        spotify_username = spotify_user["id"]
        email = spotify_user.get("email", "")

        print(f"🎵 Spotify User Logged In: {spotify_username} ({email})")

        #  User handling with bcrypt
        pending_user_id = session.pop("pending_user_id", None)
        password_hash = bcrypt.hashpw(spotify_username.encode(), bcrypt.gensalt()).decode("utf-8")

        user = None
        if pending_user_id:
            user = User.query.get(pending_user_id)

        if not user:
            user = User.query.filter_by(username=spotify_username).first()

        if not user:
            user = User(
                username=spotify_username,
                password_hash=password_hash
            )
            db.session.add(user)
            db.session.commit()

        # ✅ Generate JWT
        jwt_token = create_access_token(identity={
            "id": user.id,
            "spotify_linked": True
        })

        return {
                   "message": "Spotify login successful",
                   "access_token": jwt_token,
                   "user": user_schema.dump(user),
                   "spotify_profile": {
                       "id": spotify_username,
                       "email": email
                   }
               }, 200

    except Exception as e:
        print(f" Spotify Callback Error: {str(e)}")
        return {"error": "Spotify authentication failed", "details": str(e)}, 500