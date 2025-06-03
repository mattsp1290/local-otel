"""
Service client wrappers with automatic trace propagation
"""

import httpx
from typing import Dict, Any, Optional
from opentelemetry import trace
from opentelemetry.propagate import inject

tracer = trace.get_tracer("test-service-clients")


class BaseServiceClient:
    """Base class for service clients with tracing support"""
    
    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.base_url = base_url
        self.client = client
        
    def _inject_trace_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Inject OpenTelemetry trace context into headers"""
        headers = headers or {}
        inject(headers)
        return headers
    
    async def _request(
        self, 
        method: str, 
        path: str, 
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with trace propagation"""
        url = f"{self.base_url}{path}"
        headers = self._inject_trace_headers(headers)
        
        with tracer.start_as_current_span(f"{method} {path}") as span:
            span.set_attributes({
                "http.method": method,
                "http.url": url,
                "service.name": self.__class__.__name__
            })
            
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            
            span.set_attribute("http.status_code", response.status_code)
            
            if response.status_code >= 400:
                span.set_attribute("error", True)
                span.set_attribute("error.message", response.text[:200])
            
            return response


class AuthServiceClient(BaseServiceClient):
    """Client for Auth Service API"""
    
    async def register(self, email: str, username: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        response = await self._request(
            "POST",
            "/register",
            json={
                "email": email,
                "username": username,
                "password": password
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login user"""
        response = await self._request(
            "POST",
            "/login",
            json={
                "email": email,
                "password": password
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate authentication token"""
        response = await self._request(
            "GET",
            "/validate",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    
    async def refresh_token(self, token: str) -> Dict[str, Any]:
        """Refresh authentication token"""
        response = await self._request(
            "POST",
            "/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    
    async def logout(self, token: str) -> None:
        """Logout user"""
        response = await self._request(
            "POST",
            "/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()


class UserProfileServiceClient(BaseServiceClient):
    """Client for User Profile Service API"""
    
    def __init__(self, base_url: str, client: httpx.AsyncClient, token: Optional[str] = None):
        super().__init__(base_url, client)
        self.token = token
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers if token is available"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile"""
        response = await self._request(
            "GET",
            f"/{user_id}",
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def create_or_update_profile(
        self, 
        user_id: str,
        display_name: str,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create or update user profile"""
        response = await self._request(
            "POST",
            f"/{user_id}/profile",
            headers=self._get_auth_headers(),
            json={
                "display_name": display_name,
                "bio": bio,
                "avatar_url": avatar_url
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def follow_user(self, user_id: str) -> Dict[str, Any]:
        """Follow a user"""
        response = await self._request(
            "POST",
            f"/{user_id}/follow",
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def unfollow_user(self, user_id: str) -> Dict[str, Any]:
        """Unfollow a user"""
        response = await self._request(
            "DELETE",
            f"/{user_id}/follow",
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_followers(
        self, 
        user_id: str, 
        limit: int = 20, 
        offset: int = 0
    ) -> list[Dict[str, Any]]:
        """Get user's followers"""
        response = await self._request(
            "GET",
            f"/{user_id}/followers",
            headers=self._get_auth_headers(),
            params={"limit": limit, "offset": offset}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_following(
        self, 
        user_id: str, 
        limit: int = 20, 
        offset: int = 0
    ) -> list[Dict[str, Any]]:
        """Get users that this user follows"""
        response = await self._request(
            "GET",
            f"/{user_id}/following",
            headers=self._get_auth_headers(),
            params={"limit": limit, "offset": offset}
        )
        response.raise_for_status()
        return response.json()
    
    async def search_users(self, query: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Search for users"""
        response = await self._request(
            "GET",
            "/search",
            headers=self._get_auth_headers(),
            params={"q": query, "limit": limit, "offset": offset}
        )
        response.raise_for_status()
        return response.json()


class FeedServiceClient(BaseServiceClient):
    """Client for Feed Service API (placeholder for when implemented)"""
    
    def __init__(self, base_url: str, client: httpx.AsyncClient, token: Optional[str] = None):
        super().__init__(base_url, client)
        self.token = token
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers if token is available"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    async def create_post(self, content: str, media_urls: Optional[list[str]] = None) -> Dict[str, Any]:
        """Create a new post"""
        # Mock implementation until Feed Service is complete
        return {
            "id": "mock-post-id",
            "user_id": "mock-user-id",
            "content": content,
            "media_urls": media_urls or [],
            "created_at": "2024-01-01T00:00:00Z"
        }
    
    async def get_timeline(self, limit: int = 20, offset: int = 0) -> list[Dict[str, Any]]:
        """Get user's timeline"""
        # Mock implementation
        return []
    
    async def like_post(self, post_id: str) -> None:
        """Like a post"""
        # Mock implementation
        pass
    
    async def unlike_post(self, post_id: str) -> None:
        """Unlike a post"""
        # Mock implementation
        pass


class ServiceClients:
    """Container for all service clients"""
    
    def __init__(
        self, 
        http_client: httpx.AsyncClient,
        auth_url: str,
        user_url: str,
        feed_url: str,
        token: Optional[str] = None
    ):
        self.auth = AuthServiceClient(auth_url, http_client)
        self.user = UserProfileServiceClient(user_url, http_client, token)
        self.feed = FeedServiceClient(feed_url, http_client, token)
    
    def with_token(self, token: str) -> 'ServiceClients':
        """Create new instance with authentication token"""
        return ServiceClients(
            self.auth.client,
            self.auth.base_url,
            self.user.base_url,
            self.feed.base_url,
            token
        )
