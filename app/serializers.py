from marshmallow import Schema, fields
from app.models import Playlist, Track, User  # ✅ Corrected import


# ✅ User Serializer
class UserSchema(Schema):
    id = fields.Int(dump_only=True)  # Auto-generated ID
    username = fields.Str(required=True)  # Username (Required)

    class Meta:
        model = User  # ✅ Automatically map to User model


# ✅ Playlist Serializer
class PlaylistSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)  # Links to User
    name = fields.Str(required=True)  # Playlist name
    description = fields.Str()
    created_at = fields.DateTime(dump_only=True)  # ✅ Read-Only Timestamp
    tracks = fields.Nested("TrackSchema", many=True)  # ✅ Include tracks in playlist

    class Meta:
        model = Playlist  # ✅ Automatically map to Playlist model


# ✅ Track Serializer
class TrackSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)  # Track Name
    artist = fields.Str(required=True)  # Artist Name
    album = fields.Str()  # Album Name
    playlist_id = fields.Int(required=True)  # Links to Playlist
    playlist = fields.Nested("PlaylistSchema", only=["id", "name"])  # ✅ Include playlist info

    class Meta:
        model = Track  # ✅ Automatically map to Track model


# ✅ Initialize Serializers
user_schema = UserSchema()
playlist_schema = PlaylistSchema()
track_schema = TrackSchema()

# ✅ Serialize Multiple Objects
users_schema = UserSchema(many=True)
playlists_schema = PlaylistSchema(many=True)
tracks_schema = TrackSchema(many=True)
