# Authentication System Documentation

## Overview

This project implements a Supabase JWT token-based authentication system for all API endpoints (except the health check endpoint). The authentication system validates JWT tokens issued by Supabase against Supabase's JWKS (JSON Web Key Set) endpoint.

## How It Works

1. **Frontend Authentication**: The frontend uses Supabase authentication to sign in users and obtain a JWT token.
2. **Token Validation**: All protected API endpoints validate the JWT token against Supabase's JWKS endpoint.
3. **Access Control**: Only requests with valid, unexpired tokens are granted access to the protected endpoints.
4. **User Identification**: The user ID is extracted from the validated token and used in the business logic.

## Implementation Details

### auth.py

The `auth.py` module contains the core authentication logic:

- `SupabaseJWTValidator`: Class responsible for validating JWT tokens against Supabase
- `get_current_user`: FastAPI dependency that validates the token and returns the payload
- `get_user_id_from_token`: Helper function to extract the user ID from the token payload

### API Endpoints

All endpoints in `api.py` (except `/healthz`) are protected by the authentication system:

- They use the `get_current_user` dependency to validate tokens
- They extract the user ID from the token payload instead of accepting it as a parameter
- They return 401 Unauthorized for invalid tokens
- They return 403 Forbidden for requests without an Authorization header

### Dependencies

The authentication system requires the following additional dependencies:
- `pyjwt>=2.8.0`: For JWT token validation
- `cryptography>=41.0.0`: For cryptographic operations

## Usage

### Frontend Integration

1. Authenticate the user using Supabase Auth
2. Obtain the JWT token from the Supabase session
3. Include the token in the Authorization header of all API requests:

```
Authorization: Bearer <your-jwt-token>
```

### Backend Implementation

The authentication is implemented as a FastAPI dependency:

```python
from auth import get_current_user

@router.post("/voice")
async def create_voice_session(
    name: Optional[str] = "NA", 
    email: Optional[str] = "NA",
    token_payload: dict = Depends(get_current_user)  # This validates the token
) -> VoiceSessionResponse:
    # Extract user_id from token
    user_id = get_user_id_from_token(token_payload)
    # Continue with business logic...
```

## Error Handling

The authentication system returns appropriate HTTP status codes:

- `401 Unauthorized`: Invalid, expired, or malformed token
- `403 Forbidden`: Missing Authorization header
- `500 Internal Server Error`: Issues with the Supabase JWKS endpoint

## Testing

The test suite includes tests that verify the authentication behavior:

- Tests for endpoints without authentication tokens (should return 403)
- Tests for endpoints with invalid tokens (should return 401)
- Health check endpoint tests (should work without authentication)

## Environment Variables

The authentication system requires the following environment variables:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key (for client initialization)

These are the same variables required for the database integration.