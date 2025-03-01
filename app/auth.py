from flask import request, jsonify
from flask_jwt_extended import create_access_token
from app import db
from app.models import User
from app.serializers import user_schema
import bcrypt


def register_user():
    """Register a new user and return a JWT token."""
    try:
        data = request.get_json()

        # ✅ Validate input
        if not data or "username" not in data or "password" not in data:
            return jsonify({"error": "Missing username or password"}), 400

        # ✅ Check if user already exists
        existing_user = User.query.filter_by(username=data["username"]).first()
        if existing_user:
            return jsonify({"error": "Username already exists"}), 400

        # ✅ Hash the password
        hashed_pw = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # ✅ Create and save user
        new_user = User(username=data["username"], password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        # ✅ Generate JWT token
        token = create_access_token(identity=new_user.id)

        response = {
            "message": "User registered successfully!",
            "access_token": token,
            "user": user_schema.dump(new_user)
        }

        return jsonify(response), 201
    except Exception as e:
        return jsonify({"error": "Failed to register user", "details": str(e)}), 500


def login_user():
    """Login user and return JWT token."""
    try:
        data = request.get_json()

        # ✅ Validate input
        if not data or "username" not in data or "password" not in data:
            return jsonify({"error": "Missing username or password"}), 400

        # ✅ Fetch user from database
        user = User.query.filter_by(username=data["username"]).first()

        if not user:
            return jsonify({"error": "Invalid username or password"}), 401

        # ✅ Validate password
        if not bcrypt.checkpw(data["password"].encode('utf-8'), user.password_hash.encode('utf-8')):
            return jsonify({"error": "Invalid username or password"}), 401

        # ✅ Generate JWT Token
        token = create_access_token(identity=str(user.id))

        response = {
            "message": "Login successful",
            "access_token": token,
            "user": user_schema.dump(user)
        }

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": "Failed to login", "details": str(e)}), 500
