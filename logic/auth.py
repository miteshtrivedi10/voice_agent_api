"""Supabase JWT authentication module for FastAPI."""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError
import httpx
from loguru import logger

# Import settings
from logic.config import settings

# Supabase configuration
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY


# JWT configuration
JWT_AUDIENCE = "authenticated"

# Security scheme for FastAPI
security = HTTPBearer()


class SupabaseJWTValidator:
    """Validates Supabase JWT tokens."""
    
    def __init__(self):
        self.supabase_url = SUPABASE_URL
        self.supabase_key = SUPABASE_KEY
        
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token against Supabase."""
        try:
            logger.info("Starting token validation")
            
            # For Supabase with external providers, we need to validate differently
            # First, let's try to decode the token without verification to get the payload
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            logger.info(f"Unverified payload: {unverified_payload}")
            
            # Check if token is expired
            import time
            if unverified_payload.get("exp", 0) < time.time():
                logger.error("Token has expired")
                raise HTTPException(status_code=401, detail="Token has expired")
            
            # Validate audience
            if unverified_payload.get("aud") != JWT_AUDIENCE:
                logger.error("Invalid audience")
                raise HTTPException(status_code=401, detail="Invalid audience")
            
            # Validate with Supabase API
            logger.info("Validating token with Supabase API")
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "apikey": self.supabase_key
                }
                response = await client.get(
                    f"{self.supabase_url}/auth/v1/user",
                    headers=headers
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    logger.info("Token validated successfully with Supabase API")
                    # Merge user data with token payload
                    unverified_payload.update(user_data)
                    return unverified_payload
                elif response.status_code == 401:
                    logger.error("Invalid token according to Supabase API")
                    raise HTTPException(status_code=401, detail="Invalid token")
                else:
                    logger.error(f"Supabase API returned status code {response.status_code}")
                    raise HTTPException(status_code=500, detail="Failed to validate token")
                    
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidAudienceError:
            logger.error("Invalid audience")
            raise HTTPException(status_code=401, detail="Invalid audience")
        except PyJWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


# Create a global instance
jwt_validator = SupabaseJWTValidator()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current user from JWT token."""
    try:
        token = credentials.credentials
        logger.info(f"Received token: {token[:10]}...")  # Log first 10 chars of token for debugging
        payload = await jwt_validator.validate_token(token)
        logger.info(f"Token validated successfully for user: {payload.get('sub')}")
        return payload
    except HTTPException as e:
        logger.error(f"HTTPException in get_current_user: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def get_user_id_from_token(token_payload: Dict[str, Any]) -> str:
    """Extract user ID from token payload."""
    # Supabase stores user ID in the 'sub' field
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    return user_id


def get_user_info_from_token(token_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract user information from token payload."""
    user_id = token_payload.get("sub") or token_payload.get("uid")
    full_name = token_payload.get("full_name") or token_payload.get("name")
    email = token_payload.get("email")
    user_name = token_payload.get("user_name")  # Extract user_name from token
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    
    if not full_name:
        raise HTTPException(status_code=401, detail="Invalid token: missing full name")
    
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token: missing email")
    
    # user_name is optional but recommended
    if not user_name:
        # Fallback to generating a user_name from email if not provided
        user_name = email.split("@")[0] if email else "user"
    
    return {
        "user_id": user_id,
        "full_name": full_name,
        "email": email,
        "user_name": user_name  # Include user_name in returned info
    }