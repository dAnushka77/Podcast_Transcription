import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def get_spotify_access_token():
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_response = requests.post(auth_url, {
        'grant_type': 'client_credentials',
        'client_id': os.getenv("SPOTIFY_CLIENT_ID"),
        'client_secret': os.getenv("SPOTIFY_CLIENT_SECRET")
    })
    
    if auth_response.status_code == 200:
        auth_response_data = auth_response.json()
        return auth_response_data['access_token']
    else:
        st.error(f"Failed to get access token: {auth_response.status_code} - {auth_response.text}")
        return None
    
def search_podcasts(person_name, access_token, limit = 5):
    search_url = 'https://api.spotify.com/v1/search'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    params = {
        'q': person_name,
        'type': 'episode',
        'market': 'US',
        'limit': limit
    }
    
    response = requests.get(search_url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to search podcasts: {response.status_code} - {response.text}")
        return None
    
def get_most_recent_podcast(person_name, num_results = 5):
    access_token = get_spotify_access_token()
    
    if access_token:
        search_results = search_podcasts(person_name, access_token, num_results)
        
        if search_results and 'episodes' in search_results and search_results['episodes']['items']:
            return search_results['episodes']['items']
        else:
            return []
    else:
        return []
    
def transcribe_audio(audio_file_path,  groq_api_key):
    transcription_url = 'https://api.groq.com/openai/v1/audio/transcriptions'
    headers = {
        'Authorization': f'Bearer {groq_api_key}',
    }    
    
    data = {
        'model': 'whisper-large-v3'
    }
    
    with open(audio_file_path, 'rb') as audio_file:
        files = {'file': ('audio.mp3', audio_file)}
        response = requests.post(transcription_url, headers=headers, data=data, files=files)
        
    if response.status_code == 200:
        transcription_data = response.json()
        return transcription_data.get('text', 'No text returned from API.')
    else:
        return f"Transcription failed: {response.status_code} - {response.text}"

def save_transcription_to_file(transcription_text, output_file_path):
    with open(output_file_path, 'w') as file:
        file.write(transcription_text)

st.title('Podcast Transcription App')

person_name = st.text_input('Enter the name of the person to search for:', 'Joe Rogan')

# Button click to initiate search
if st.button('Search Podcasts'):
    st.session_state.podcasts = get_most_recent_podcast(person_name, num_results=5)
    st.session_state.selected_index = 1

# Check if podcasts have been fetched
if 'podcasts' in st.session_state and st.session_state.podcasts:
    st.write(f"Podcasts featuring {person_name}:")
    
    # Display podcasts
    for i, podcast in enumerate(st.session_state.podcasts):
        st.write(f"{i + 1}. {podcast['name']} - {podcast['release_date']} - {podcast['description'][:100]}...")
    
    # Dropdown for selecting a podcast
    st.session_state.selected_index = st.number_input(
        'Select a podcast to transcribe (1-5):', 
        min_value=1, 
        max_value=len(st.session_state.podcasts), 
        value=st.session_state.selected_index
    )

    # Process selection and transcribe
    selected_podcast = st.session_state.podcasts[st.session_state.selected_index - 1]
    podcast_link = selected_podcast['external_urls']['spotify']
    audio_file_url = selected_podcast.get('audio_preview_url')
    
    st.write(f"Selected podcast: {selected_podcast['name']}")
    st.write(f"Podcast link: {podcast_link}")
    
    if audio_file_url:
        audio_response = requests.get(audio_file_url, stream=True)
        if audio_response.status_code == 200:
            audio_file_path = 'downloaded_podcast.mp3'
            with open(audio_file_path, 'wb') as audio_file:
                for chunk in audio_response.iter_content(chunk_size=8192):
                    audio_file.write(chunk)
            
            transcription_text = transcribe_audio(audio_file_path, os.getenv("GROQ_API_KEY"))
            output_file_path = 'transcription.txt'
            save_transcription_to_file(transcription_text, output_file_path)
            
            st.write(f"Transcription saved to {output_file_path}")
            st.write("Transcription:")
            st.write(transcription_text)
        else:
            st.error(f"Failed to download audio: {audio_response.status_code} - {audio_response.text}")
    else:
        st.write("No audio preview available for this podcast.")