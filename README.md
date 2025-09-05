# Voice Agent API

A FastAPI-based API for handling voice sessions and file uploads with Supabase integration.

## Features

- Voice session creation with LiveKit integration
- PDF file upload with validation
- Asynchronous logging with Loguru
- Supabase database integration
- Supabase JWT token authentication
- Comprehensive error handling

## Setup

1. Install dependencies:
   ```bash
   uv install
   ```

2. Set environment variables:
   ```bash
   export LIVEKIT_URL=your_livekit_url
   export LIVEKIT_API_KEY=your_api_key
   export LIVEKIT_API_SECRET=your_api_secret
   export SUPABASE_URL=your_supabase_url
   export SUPABASE_KEY=your_supabase_key
   export UPLOAD_DIRECTORY=/absolute/path/to/upload/directory
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Authentication

All API endpoints (except `/healthz`) require a valid Supabase JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

The token is validated against Supabase's JWKS endpoint. Invalid or expired tokens will result in a 401 Unauthorized response.

The JWT token must contain the following claims:
- `sub` or `uid`: User ID
- `full_name` or `name`: User's full name
- `email`: User's email address

These values are extracted from the token and used in various parts of the application.

## File Uploads

Uploaded files are stored in a directory specified by the `UPLOAD_DIRECTORY` environment variable. If not set, files will be stored in the `uploaded_files` directory relative to the application root.

## API Endpoints

- `POST /voice` - Create a new voice session (requires authentication)
- `POST /upload-files` - Upload a PDF file (requires authentication)
- `GET /healthz` - Health check endpoint (no authentication required)

## Database

The application uses Supabase for data persistence with the following tables:

- `user_voice_sessions` - Stores voice session information
- `file_details` - Stores uploaded file metadata

## Logging

Logs are stored in the `logs/` directory with rotation.