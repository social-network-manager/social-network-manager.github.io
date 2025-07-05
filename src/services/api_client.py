import requests
import time
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiting utility for API calls"""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = datetime.now()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < timedelta(minutes=1)]
        
        if len(self.calls) >= self.calls_per_minute:
            # Calculate wait time
            oldest_call = min(self.calls)
            wait_time = 60 - (now - oldest_call).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
        
        self.calls.append(now)

class APIResponse:
    """Standardized API response wrapper"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None, 
                 status_code: int = None, platform_response: Dict = None):
        self.success = success
        self.data = data
        self.error = error
        self.status_code = status_code
        self.platform_response = platform_response or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self):
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'status_code': self.status_code,
            'platform_response': self.platform_response,
            'timestamp': self.timestamp.isoformat()
        }

class BasePlatformClient(ABC):
    """Abstract base class for platform API clients"""
    
    def __init__(self, credentials: Dict[str, Any], rate_limit: int = 60):
        self.credentials = credentials
        self.rate_limiter = RateLimiter(rate_limit)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SocialMediaManager/1.0'
        })
    
    @abstractmethod
    def authenticate(self) -> APIResponse:
        """Authenticate with the platform"""
        pass
    
    @abstractmethod
    def post_content(self, content: str, media_files: List[str] = None, 
                    **kwargs) -> APIResponse:
        """Post content to the platform"""
        pass
    
    @abstractmethod
    def get_user_info(self) -> APIResponse:
        """Get authenticated user information"""
        pass
    
    def _make_request(self, method: str, url: str, **kwargs) -> APIResponse:
        """Make HTTP request with rate limiting and error handling"""
        self.rate_limiter.wait_if_needed()
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Log request for debugging
            logger.info(f"{method} {url} - Status: {response.status_code}")
            
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return APIResponse(
                    success=False,
                    error=error_msg,
                    status_code=response.status_code,
                    platform_response=response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                )
            
            # Try to parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = response.text
            
            return APIResponse(
                success=True,
                data=data,
                status_code=response.status_code,
                platform_response=data if isinstance(data, dict) else {}
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return APIResponse(
                success=False,
                error=f"Request failed: {str(e)}"
            )

class FacebookClient(BasePlatformClient):
    """Facebook Graph API client"""
    
    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials, rate_limit=200)  # Facebook allows 200 calls/hour
        self.base_url = "https://graph.facebook.com/v18.0"
        self.access_token = credentials.get('access_token')
        self.page_id = credentials.get('page_id')
    
    def authenticate(self) -> APIResponse:
        """Verify Facebook access token"""
        url = f"{self.base_url}/me"
        params = {'access_token': self.access_token}
        
        return self._make_request('GET', url, params=params)
    
    def post_content(self, content: str, media_files: List[str] = None, **kwargs) -> APIResponse:
        """Post content to Facebook page"""
        if not self.page_id:
            return APIResponse(success=False, error="Page ID required for posting")
        
        url = f"{self.base_url}/{self.page_id}/feed"
        data = {
            'message': content,
            'access_token': self.access_token
        }
        
        # Add link if provided
        if 'link' in kwargs:
            data['link'] = kwargs['link']
        
        # TODO: Handle media file uploads
        if media_files:
            # For now, just log that media files were provided
            logger.info(f"Media files provided but not yet implemented: {media_files}")
        
        return self._make_request('POST', url, data=data)
    
    def get_user_info(self) -> APIResponse:
        """Get Facebook user/page information"""
        url = f"{self.base_url}/me"
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,email,picture'
        }
        
        return self._make_request('GET', url, params=params)

class TwitterClient(BasePlatformClient):
    """X (Twitter) API v2 client"""
    
    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials, rate_limit=300)  # Conservative rate limit
        self.base_url = "https://api.twitter.com/2"
        self.bearer_token = credentials.get('bearer_token')
        self.access_token = credentials.get('access_token')
        self.access_token_secret = credentials.get('access_token_secret')
        
        if self.bearer_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.bearer_token}'
            })
    
    def authenticate(self) -> APIResponse:
        """Verify Twitter credentials"""
        url = f"{self.base_url}/users/me"
        
        return self._make_request('GET', url)
    
    def post_content(self, content: str, media_files: List[str] = None, **kwargs) -> APIResponse:
        """Post tweet to Twitter"""
        url = f"{self.base_url}/tweets"
        
        data = {
            'text': content
        }
        
        # TODO: Handle media file uploads and other tweet features
        if media_files:
            logger.info(f"Media files provided but not yet implemented: {media_files}")
        
        headers = {'Content-Type': 'application/json'}
        
        return self._make_request('POST', url, json=data, headers=headers)
    
    def get_user_info(self) -> APIResponse:
        """Get Twitter user information"""
        url = f"{self.base_url}/users/me"
        params = {
            'user.fields': 'id,name,username,profile_image_url,public_metrics'
        }
        
        return self._make_request('GET', url, params=params)

class LinkedInClient(BasePlatformClient):
    """LinkedIn API client"""
    
    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials, rate_limit=500)  # LinkedIn allows 500 calls/day
        self.base_url = "https://api.linkedin.com/v2"
        self.access_token = credentials.get('access_token')
        
        if self.access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}'
            })
    
    def authenticate(self) -> APIResponse:
        """Verify LinkedIn access token"""
        url = f"{self.base_url}/people/~"
        
        return self._make_request('GET', url)
    
    def post_content(self, content: str, media_files: List[str] = None, **kwargs) -> APIResponse:
        """Post content to LinkedIn"""
        url = f"{self.base_url}/ugcPosts"
        
        # Get user URN first
        user_info = self.get_user_info()
        if not user_info.success:
            return user_info
        
        user_urn = f"urn:li:person:{user_info.data.get('id')}"
        
        data = {
            "author": user_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        
        return self._make_request('POST', url, json=data, headers=headers)
    
    def get_user_info(self) -> APIResponse:
        """Get LinkedIn user information"""
        url = f"{self.base_url}/people/~"
        params = {
            'projection': '(id,firstName,lastName,profilePicture(displayImage~:playableStreams))'
        }
        
        return self._make_request('GET', url, params=params)

class APIClientFactory:
    """Factory for creating platform-specific API clients"""
    
    CLIENTS = {
        'facebook': FacebookClient,
        'twitter': TwitterClient,
        'linkedin': LinkedInClient,
        # Add more clients as they are implemented
    }
    
    @classmethod
    def create_client(cls, platform: str, credentials: Dict[str, Any]) -> Optional[BasePlatformClient]:
        """Create API client for specified platform"""
        client_class = cls.CLIENTS.get(platform.lower())
        
        if not client_class:
            logger.error(f"No client available for platform: {platform}")
            return None
        
        try:
            return client_class(credentials)
        except Exception as e:
            logger.error(f"Failed to create {platform} client: {str(e)}")
            return None
    
    @classmethod
    def get_supported_platforms(cls) -> List[str]:
        """Get list of platforms with API client support"""
        return list(cls.CLIENTS.keys())

