from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # ✅ One-to-Many Relationship (User → Playlists)
    playlists = db.relationship('Playlist', backref='user', lazy=True, cascade="all, delete-orphan")


class Playlist(db.Model):
    __tablename__ = "playlist"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete="CASCADE", name="fk_playlist_user"),  # ✅ Added constraint name
        nullable=False
    )
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    spotify_id = db.Column(db.String(100), nullable=True)  # ✅ Store Spotify Playlist ID
    # ✅ One-to-Many Relationship (Playlist → Tracks)
    tracks = db.relationship('Track', backref='playlist', lazy=True, cascade="all, delete-orphan")


class Track(db.Model):
    __tablename__ = "track"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    album = db.Column(db.String(200))
    playlist_id = db.Column(
        db.Integer,
        db.ForeignKey('playlist.id', ondelete="CASCADE", name="fk_track_playlist"),  # ✅ Added constraint name
        nullable=False
    )
