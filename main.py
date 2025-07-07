import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# Get the authenticated connection 
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
    redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
    scope=["user-library-read", "playlist-read-private", "playlist-modify-private"]
))


# Get saved tracks using API
saved_tracks = sp.current_user_saved_tracks()

# Create dataframe of saved tracks 
track_list = []

while saved_tracks:
    for item in saved_tracks['items']:
        track = item['track']
        track_info = {'name' : track['name'],
                    'artist' : track['artists'][0]['name'],
                    'album' : track['album']['name'],
                    'id' : track['id']
                    }
        track_list.append(track_info)

    if saved_tracks['next']: 
        saved_tracks = sp.next(saved_tracks)
    else:
        break
        
df_saved_tracks = pd.DataFrame(track_list)


# Get saved albums using API
saved_albums = sp.current_user_saved_albums()

# Create dataframe of tracks within saved albums
album_track_list = []

while saved_albums:
    for item in saved_albums['items']:
        album = item['album']
        album_name = album['name']  
        
       
        tracks = sp.album_tracks(album['id'])
        
        while tracks:
            for track in tracks['items']:
                album_track_info = {
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': album_name,  
                    'id': track['id']
                }
                album_track_list.append(album_track_info)  
            
            
            if tracks['next']:
                tracks = sp.next(tracks)
            else:
                break
    

    if saved_albums['next']:
        saved_albums = sp.next(saved_albums)
    else: 
        break

df_saved_album_tracks = pd.DataFrame(album_track_list)


# Combine dataframes (saved tracks + tracks from saved albums)
df_tracks = pd.concat([df_saved_tracks, df_saved_album_tracks])


# Get rid of duplicates
df_tracks = df_tracks.drop_duplicates('id')


# Get all saved playlists using API

playlists = sp.current_user_playlists()

# Create dataframe of playlist info
playlist_list =[]
while playlists:
    for item in playlists['items']:
        playlist_list.append({'name': item['name'], 'id': item['id']})
        
    if playlists['next']: 
        playlists = sp.next(playlists)
    else:
        break  

df_playlists = pd.DataFrame(playlist_list)      
    
# Check if master playlist exists   
master_playlist_exists = df_playlists['name'].str.lower().str.contains('master playlist').any()

# If it does:
if master_playlist_exists:
    print('Master playlist found, track list will be modified according to the current library')
    
    
    # Get playlist id
    master_playlist_mask = df_playlists['name'].str.lower().str.contains('master playlist')
    existing_master_playlist_id = existing_master_playlist_id = df_playlists[master_playlist_mask]['id'].iloc[0]
    
    # Get existing tracks in mastser playlist
    existing_master_playlist_tracks = []
    existing_playlist_tracks = sp.playlist_tracks(existing_master_playlist_id)
    
    while existing_playlist_tracks:
        for item in existing_playlist_tracks['items']:
            if item['track'] and item['track']['id']:
                existing_master_playlist_tracks.append(item['track']['id'])
        
        if existing_playlist_tracks['next']:
            existing_playlist_tracks = sp.next(existing_playlist_tracks)
        else:
            break
        
    # Find tracks that aren't already in the playlist
    existing_playlist_tracks_ids = set(existing_master_playlist_tracks)
    all_tracks_ids = set(df_tracks['id'].dropna())
    
    tracks_to_add = list(all_tracks_ids - existing_playlist_tracks_ids)
    
    # Add those tracks in batches to the existing playlist
    if tracks_to_add:
        batch_size = 100
        for i in range(0, len(tracks_to_add), batch_size):
            batch = tracks_to_add[i:i + batch_size]
            sp.playlist_add_items(existing_master_playlist_id, batch)


#If the master playlist doesn't exist
else:
    
    # Create new playlist
    print('Playlist not found, creating a new Master Playlist!')
    user_id = sp.current_user()['id']
    master_playlist = sp.user_playlist_create(
            user_id, 
            'Master Playlist',
            description='All tracks from saved albums and liked songs',
            public=False
        )
        
    master_playlist_id = master_playlist['id']
        
    # Get all tracks' ids
    all_track_ids = df_tracks['id'].dropna().tolist()
        
        
    # Add tracks in batches
    batch_size = 100
    for i in range(0, len(all_track_ids), batch_size):
            batch = all_track_ids[i:i + batch_size]
            sp.playlist_add_items(master_playlist_id, batch)
