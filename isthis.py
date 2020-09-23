import sys
import configparser
import spotipy
import spotipy.util as util
from track import Track


def authorize():
    config = configparser.ConfigParser()
    config.read("settings.conf")

    username = config["spotify"]["username"]
    country = config["spotify"]["country"]
    scope = config["spotify"]["scope"]
    client_id = config["spotify"]["client_id"]
    client_secret = config["spotify"]["client_secret"]
    redirect_uri = config["spotify"]["redirect_uri"]

    token = util.prompt_for_user_token(
        username,
        scope,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    sp = spotipy.Spotify(auth=token)

    return sp, username, country


def get_artist_tracks(sp, artist, country):
    artist_albums = sp.artist_albums(artist, country=country, limit=50)
    artist_name = get_artist_name(artist, artist_albums["items"])
    print("Searching for tracks by", artist_name)

    artist_tracks = []
    for album in artist_albums["items"]:
        albumtracks = sp.album_tracks(album["id"])
        for track in albumtracks["items"]:
            for trackartist in track["artists"]:
                if trackartist["uri"] == artist:
                    artist_tracks.append(track["uri"])
    print(f"Found {len(artist_tracks)} tracks")
    return artist_name, artist_tracks


def get_artist_name(artist, artist_albums):
    for album in artist_albums:
        for a in album["artists"]:
            if a["uri"] == artist:
                return a["name"]


def select_tracks(sp, country, artist_tracks):
    sorted_tracks = []
    i = 0
    while i < len(artist_tracks):
        tracks = sp.tracks(artist_tracks[i : 50 + i], market=country)
        for track in tracks["tracks"]:
            t = Track(track["name"], track["uri"], track["popularity"])
            sorted_tracks.append(t)
        i += 50
    sorted_tracks = sorted(
        sorted_tracks, key=lambda track: track.popularity, reverse=True
    )

    return sorted_tracks


def create_playlist(sp, sorted_tracks, artist_name, username, number_of_tracks):
    track_uris = [sortedTrack.uri for sortedTrack in sorted_tracks]
    pl = sp.user_playlist_create(username, "Is This " + artist_name, public=True)
    sp.user_playlist_add_tracks(username, pl["uri"], track_uris[:number_of_tracks])
    print(f"Playlist created and {number_of_tracks} songs added")


def main():
    try:
        artist = sys.argv[1]
        number_of_tracks = int(sys.argv[2])
    except Exception:
        print("Did not get artist and number of tracks arguments. Requesting input.")
        artist = input("Artist URI: ")
        number_of_tracks = int(input("Number of tracks: "))

    sp, username, country = authorize()
    artist_name, artist_tracks = get_artist_tracks(sp, artist, country)
    sorted_tracks = select_tracks(sp, country, artist_tracks)
    create_playlist(sp, sorted_tracks, artist_name, username, number_of_tracks)


if __name__ == "__main__":
    main()
