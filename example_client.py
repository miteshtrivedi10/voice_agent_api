"""
Example of how to use the authenticated API endpoints.

This script demonstrates how to make requests to the protected endpoints
using a Supabase JWT token.
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_BASE_URL = "http://localhost:8000"  # Change this to your actual API URL
# Import settings
from logic.config import settings

# For the example client, we still need to get the token from environment directly
# since it's not part of the main application settings
import os
SUPABASE_JWT_TOKEN = os.getenv("SUPABASE_JWT_TOKEN")  # Get token from environment

# Headers with authentication
headers = {
    "Authorization": f"Bearer {SUPABASE_JWT_TOKEN}"
}

def create_voice_session():
    """Example of creating a voice session with authentication."""
    url = f"{API_BASE_URL}/voice"
    params = {
        "name": "Test User",
        "email": "test@example.com"
    }
    
    response = requests.post(url, params=params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("Voice session created successfully!")
        print(f"Room name: {data['room_name']}")
        print(f"Participant name: {data['participant_name']}")
        return data
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def upload_file(file_path, subject_name):
    """Example of uploading a file with authentication."""
    url = f"{API_BASE_URL}/upload-files"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'subject_name': subject_name}
        
        response = requests.post(url, files=files, data=data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("File uploaded successfully!")
            print(f"Status: {data['status']}")
            print(f"Message: {data['message']}")
            return data
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None

# Example usage (uncomment to use)
# if __name__ == "__main__":
#     # Create a voice session
#     session_data = create_voice_session()
#     
#     # Upload a file (if you have a PDF file to upload)
#     # upload_file("path/to/your/file.pdf", "Mathematics")