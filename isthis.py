import configparser
from dataclasses import dataclass

import click
import spotipy
from rich.console import Console
from rich.table import Table

SEARCH_ARTIST_AMOUNT = 10


@dataclass
class Track:
    name: str
    uri: str
    popularity: int


def authorize() -> tuple[spotipy.Spotify, str, str]:
    config = configparser.ConfigParser()
    config.read("settings.conf")

    username = config["spotify"]["username"]
    market = config["spotify"]["market"]
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

    return sp, username, market


def get_artist_tracks_uris(
    sp: spotipy.Spotify, artist: str, market: str
) -> tuple[str, list[str]]:
    artist_albums = sp.artist_albums(artist, country=market, limit=50)
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


def get_artist_name(artist: str, artist_albums: list[dict]) -> str:
    for album in artist_albums:
        for a in album["artists"]:
            if a["uri"] == artist:
                return a["name"]
    return "Unknown Artist"


def get_track_popularity(
    sp: spotipy.Spotify, market: str, track_uris: list
) -> list[Track]:
    artist_tracks: list[Track] = []
    for i in range(0, len(track_uris), 50):
        tracks = sp.tracks(track_uris[i : i + 50], market=market)  # noqa: E203
        artist_tracks.extend(
            Track(track["name"], track["uri"], track["popularity"])
            for track in tracks["tracks"]
        )
    return sorted(artist_tracks, key=lambda track: track.popularity, reverse=True)


def create_playlist(
    sp: spotipy.Spotify,
    sorted_tracks: list,
    artist_name: str,
    username: str,
    number_of_tracks: int,
) -> None:
    selected_track_uris = [
        sortedTrack.uri for sortedTrack in sorted_tracks[:number_of_tracks]
    ]
    description = (
        "This is playlist equivalent. Generated with https://github.com/noppaz/isthis"
    )
    pl = sp.user_playlist_create(
        username, f"Is This {artist_name}", public=True, description=description
    )
    sp.user_playlist_add_tracks(username, pl["uri"], selected_track_uris)
    print(f"Playlist created and {len(selected_track_uris)} songs added")


def search_artists(sp: spotipy.Spotify, query: str) -> list:
    response: dict = sp.search(query, type="artist", limit=SEARCH_ARTIST_AMOUNT)
    artists = sorted(
        response["artists"]["items"],
        key=lambda artist: artist["popularity"],
        reverse=True,
    )

    console = Console()
    table = Table(title="Artists")

    table.add_column("", style="red", no_wrap=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Followers", style="cyan", no_wrap=True)
    table.add_column("Genres", style="cyan", no_wrap=True)
    table.add_column("URL", style="bright_black", no_wrap=True)
    table.add_column("URI", style="bright_black", no_wrap=True)

    for i, artist in enumerate(artists):
        table.add_row(
            str(i + 1),
            artist["name"],
            str(artist["followers"]["total"]),
            ", ".join(artist["genres"]),
            artist["external_urls"]["spotify"],
            artist["uri"],
        )
    console.print(table)

    return artists


@click.group()
def cli() -> None:
    pass


@cli.command(help="Create a playlist directly with the Artist URI")
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
def create(artist: str, tracks: int) -> None:
    sp, username, market = authorize()
    artist_name, track_uris = get_artist_tracks_uris(sp, artist, market)
    sorted_tracks = get_track_popularity(sp, market, track_uris)
    create_playlist(sp, sorted_tracks, artist_name, username, tracks)


@cli.command(help="Interactive search for the artist")
def search() -> None:
    sp, username, market = authorize()

    query: str = click.prompt("Search", type=click.STRING)
    artists = search_artists(sp, query)
    artist_selection: int = click.prompt(
        "Select artist",
        type=click.IntRange(1, SEARCH_ARTIST_AMOUNT),
    )
    artist = artists[artist_selection - 1]["uri"]
    artist_name, track_uris = get_artist_tracks_uris(sp, artist, market)
    sorted_tracks = get_track_popularity(sp, market, track_uris)
    tracks: int = click.prompt(
        "Number of tracks for playlist",
        default=30,
        type=click.INT,
    )
    create_playlist(sp, sorted_tracks, artist_name, username, tracks)


if __name__ == "__main__":
    cli()
