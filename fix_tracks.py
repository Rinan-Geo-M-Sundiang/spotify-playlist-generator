from app import create_app, db
from app.models import Track
from app.extensions import sp

app = create_app()

with app.app_context():
    invalid_tracks = Track.query.filter(
        (Track.spotify_track_id == None) |
        (Track.spotify_track_id == '')
    ).all()

    for track in invalid_tracks:
        try:
            # Search Spotify using track metadata
            result = sp.search(
                q=f"track:{track.name} artist:{track.artist}",
                type='track',
                limit=1
            )

            if result['tracks']['items']:
                uri = result['tracks']['items'][0]['uri']
                track.spotify_track_id = uri.split(':')[-1]
                db.session.commit()
                print(f"Fixed {track.name}")
            else:
                print(f"No Spotify match for {track.name} - needs manual fix")
        except Exception as e:
            print(f"Error fixing {track.name}: {str(e)}")