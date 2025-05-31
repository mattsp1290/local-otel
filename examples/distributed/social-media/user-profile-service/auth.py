"""
Authentication utilities for User Profile Service
"""

import os
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from opentelemetry import trace
from typing import Dict, Optional

# Auth service URL
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:3001")

# Security scheme
security = HTTPBearer()

# Get tracer
tracer = trace.get_tracer(__name__)

async def verify_token(token: str) -> Optional[Dict]:
    """Verify token with auth service"""
    with tracer.start_as_current_span("verify_token") as span:
        span.set_attributes({
            "auth.service_url": AUTH_SERVICE_URL,
            "auth.action": "verify_token"
        })
        
        try:
            async with httpx.AsyncClient() as client:
                # Propagate trace context
                headers = {}
                trace.get_current_span().context
                
                response = await client.post(
                    f"{AUTH_SERVICE_URL}/api/validate/token",
                    json={"token": token},
                    headers=headers,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("valid"):
                        span.set_attribute("auth.valid", True)
                        span.set_attribute("user.id", data["user"]["id"])
                        return data["user"]
                
                span.set_attribute("auth.valid", False)
                return None
                
        except httpx.RequestError as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service unavailable"
            )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """Get current user from token"""
    token = credentials.credentials
    
    user = await verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user
