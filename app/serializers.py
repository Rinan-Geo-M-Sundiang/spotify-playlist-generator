from marshmallow import Schema, fields
from app.models import Playlist, Track, User

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)

class PlaylistSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    name = fields.Str(required=True)
    description = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    spotify_id = fields.Str()  # ✅ Include Spotify ID
    tracks = fields.Nested("TrackSchema", many=True)

class TrackSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    artist = fields.Str(required=True)
    album = fields.Str()
    playlist_id = fields.Int(required=True)

# ✅ Initialize Serializers
user_schema = UserSchema()
playlist_schema = PlaylistSchema()
track_schema = TrackSchema()

# ✅ Serialize Multiple Objects
users_schema = UserSchema(many=True)
playlists_schema = PlaylistSchema(many=True)
tracks_schema = TrackSchema(many=True)
