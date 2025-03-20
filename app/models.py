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
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='unique_playlist_per_user'),
    )
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
    __table_args__ = (
        db.UniqueConstraint('playlist_id', 'name', name='unique_track_per_playlist'),
    )
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    album = db.Column(db.String(200))
    playlist_id = db.Column(
        db.Integer,
        db.ForeignKey('playlist.id', ondelete="CASCADE", name="fk_track_playlist"),  # ✅ Added constraint name
        nullable=False
    )
    spotify_track_id = db.Column(db.String(200), nullable=False)  # Add this new field
    # Add unique constraint
    __table_args__ = (
        db.UniqueConstraint('playlist_id', 'name', name='unique_track_per_playlist'),
    )
# Add to models.py
class Favorite(db.Model):
    __tablename__ = "favorite"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    spotify_id = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'track' or 'album'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserRating(db.Model):
    __tablename__ = "user_rating"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    spotify_track_id = db.Column(db.String(200), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TrackComment(db.Model):
    __tablename__ = "track_comment"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete="CASCADE"),
        nullable=False
    )
    track_id = db.Column(
        db.Integer,
        db.ForeignKey('track.id', ondelete="CASCADE", name="fk_comment_track"),  # Added constraint name
        nullable=False
    )
    comment = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add explicit relationship with cascade configuration
    user = db.relationship('User', backref=db.backref('comments', cascade='all, delete-orphan'))
    track = db.relationship('Track', backref=db.backref('comments', cascade='all, delete-orphan'))





