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