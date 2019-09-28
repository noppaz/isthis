import sys
import configparser
import spotipy
import spotipy.util as util
from Track import Track

def authorizeApp():
    config = configparser.ConfigParser()
    config.read('settings.conf')

    username = config['spotify']['username']
    country = config['spotify']['country']
    scope = config['spotify']['scope']
    client_id = config['spotify']['client_id']
    client_secret = config['spotify']['client_secret']
    redirect_uri = config['spotify']['redirect_uri']

    token = util.prompt_for_user_token(username,scope,client_id=client_id,client_secret=client_secret,redirect_uri=redirect_uri)
    sp = spotipy.Spotify(auth=token)

    return sp, username, country

def getArtistTracks(sp, artist, country):
    artistAlbums = sp.artist_albums(artist, country=country, limit=50)
    artistName = getArtistName(artist, artistAlbums['items'])
    print('Searching for tracks by', artistName)

    artistTracks = []
    for album in artistAlbums['items']:
        albumtracks = sp.album_tracks(album['id'])
        for track in albumtracks['items']:
            for trackartist in track['artists']:
                if trackartist['uri'] == artist:
                    artistTracks.append(track['uri'])
    print('Found %d tracks' % len(artistTracks))
    return artistName, artistTracks

def getArtistName(artist, artistAlbums):
    for album in artistAlbums:
        for a in album['artists']:
            if a['uri'] == artist:
                return a['name']

def selectTracks(sp, country, artistTracks):
    sortedTracks = []
    i = 0
    while i < len(artistTracks):
        tracks = sp.tracks(artistTracks[i:50+i], market=country)
        for track in tracks['tracks']:
            t = Track(track['name'], track['uri'], track['popularity'])
            sortedTracks.append(t)
        i += 50
    sortedTracks = sorted(sortedTracks, key=lambda track: track.popularity, reverse=True)

    return sortedTracks


def createPlaylist(sp, sortedTracks, artistName, username, numberOfTracks):
    trackURIs = [sortedTrack.uri for sortedTrack in sortedTracks]
    pl = sp.user_playlist_create(username, 'Is This ' + artistName, public=True)
    sp.user_playlist_add_tracks(username, pl['uri'], trackURIs[:numberOfTracks])
    print('Playlist created and %d songs added' % (numberOfTracks))     

def main():
    try:
        artist = sys.argv[1]
        numberOfTracks = int(sys.argv[2])
    except:
        print('Did not get artist and number of tracks arguments. Requesting input.')
        artist = input('Artist URI: ')
        numberOfTracks = int(input('Number of tracks: '))

    sp, username, country = authorizeApp()
    artistName, artistTracks = getArtistTracks(sp, artist, country)
    sortedTracks = selectTracks(sp, country, artistTracks)
    createPlaylist(sp, sortedTracks, artistName, username, numberOfTracks)

main()