"""Supabase JWT authentication module for FastAPI."""
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError
import httpx
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project-url.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")

# JWT configuration
JWT_AUDIENCE = "authenticated"

# Security scheme for FastAPI
security = HTTPBearer()


class SupabaseJWTValidator:
    """Validates Supabase JWT tokens."""
    
    def __init__(self):
        self.supabase_url = SUPABASE_URL
        self.supabase_key = SUPABASE_KEY
        self.jwks_url = f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
        self.jwks_cache: Optional[Dict[str, Any]] = None
        
    async def get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Supabase."""
        if self.jwks_cache is None:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self.jwks_url)
                    response.raise_for_status()
                    self.jwks_cache = response.json()
            except Exception as e:
                logger.error(f"Failed to fetch JWKS: {e}")
                raise HTTPException(status_code=500, detail="Failed to fetch JWKS")
        return self.jwks_cache
        
    def get_signing_key(self, kid: str, jwks: Dict[str, Any]):
        """Extract signing key from JWKS."""
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return jwt.algorithms.RSAAlgorithm.from_jwk(key)
        raise HTTPException(status_code=401, detail="Invalid token signing key")
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token against Supabase."""
        try:
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise HTTPException(status_code=401, detail="Invalid token header")
            
            # Get JWKS
            jwks = await self.get_jwks()
            
            # Get signing key
            signing_key = self.get_signing_key(kid, jwks)
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[unverified_header.get("alg", "RS256")],
                audience=JWT_AUDIENCE,
                issuer=f"{self.supabase_url}/auth/v1"
            )
            
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidAudienceError:
            raise HTTPException(status_code=401, detail="Invalid audience")
        except jwt.InvalidIssuerError:
            raise HTTPException(status_code=401, detail="Invalid issuer")
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
        payload = await jwt_validator.validate_token(token)
        return payload
    except HTTPException:
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