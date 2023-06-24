import click
import configparser
from dataclasses import dataclass
from typing import List, Tuple

import spotipy


@dataclass
class Track:
    name: str
    uri: str
    popularity: int


def authorize() -> Tuple[spotipy.Spotify, str, str]:
    config = configparser.ConfigParser()
    config.read("settings.conf")

    username = config["spotify"]["username"]
    country = config["spotify"]["country"]
    scope = config["spotify"]["scope"]
    client_id = config["spotify"]["client_id"]
    client_secret = config["spotify"]["client_secret"]
    redirect_uri = config["spotify"]["redirect_uri"]

    token = spotipy.util.prompt_for_user_token(
        username,
        scope,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    sp = spotipy.Spotify(auth=token)

    return sp, username, country


def get_artist_tracks_uris(
    sp: spotipy.Spotify, artist: str, country: str
) -> Tuple[str, List[str]]:
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


def get_artist_name(artist: str, artist_albums: List[dict]) -> str:
    for album in artist_albums:
        for a in album["artists"]:
            if a["uri"] == artist:
                return a["name"]
    return "Unknown Artist"


def get_track_popularity(
    sp: spotipy.Spotify, country: str, artist_tracks: list
) -> List[Track]:
    sorted_tracks = []
    i = 0
    while i < len(artist_tracks):
        tracks = sp.tracks(artist_tracks[i : 50 + i], market=country)  # noqa: E203
        for track in tracks["tracks"]:
            t = Track(track["name"], track["uri"], track["popularity"])
            sorted_tracks.append(t)
        i += 50
    sorted_tracks = sorted(
        sorted_tracks, key=lambda track: track.popularity, reverse=True
    )

    return sorted_tracks


def create_playlist(
    sp: spotipy.Spotify,
    sorted_tracks: list,
    artist_name: str,
    username: str,
    number_of_tracks: int,
) -> None:
    track_uris = [sortedTrack.uri for sortedTrack in sorted_tracks]
    tracks_to_add = track_uris[:number_of_tracks]
    description = (
        "This is playlist equivalent. Generated with https://github.com/noppaz/isthis"
    )
    pl = sp.user_playlist_create(
        username, f"Is This {artist_name}", public=True, description=description
    )
    sp.user_playlist_add_tracks(username, pl["uri"], tracks_to_add)
    print(f"Playlist created and {len(tracks_to_add)} songs added")


@click.command()
@click.option(
    "--artist",
    prompt="Artist URI",
    type=click.STRING,
    help="Artist URI, example: spotify:artist:3WrFJ7ztbogyGnTHbHJFl2",
)
@click.option(
    "--tracks",
    default=30,
    prompt="Number of tracks",
    type=click.INT,
    help="Number of tracks for playlist",
)
def is_this(artist: str, tracks: int):
    sp, username, country = authorize()
    artist_name, track_uris = get_artist_tracks_uris(sp, artist, country)
    sorted_tracks = get_track_popularity(sp, country, track_uris)
    create_playlist(sp, sorted_tracks, artist_name, username, tracks)


if __name__ == "__main__":
    is_this()
