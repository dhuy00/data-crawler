"""
HTTP client with retry and rate limiting support.

Provides session management for API requests.
"""
import random
from typing import Dict, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from core.logger import logger
from core.retry_handler import rate_limit_wait
from config.settings import settings
from config.constants import DEFAULT_HEADERS


class HTTPClient:
    """HTTP client with built-in retry and rate limiting."""

    def __init__(
        self,
        timeout: int = settings.HTTP_TIMEOUT,
        max_retries: int = settings.HTTP_RETRIES,
        backoff_factor: float = settings.HTTP_BACKOFF_FACTOR,
    ):
        """
        Initialize HTTP client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            backoff_factor: Backoff factor for retries
        """
        self.timeout = timeout
        self.session = requests.Session()
        self._configure_retries(max_retries, backoff_factor)
        self._set_user_agent()

    def _configure_retries(self, max_retries: int, backoff_factor: float) -> None:
        """Configure retry strategy for session."""
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _set_user_agent(self) -> None:
        """Set random user agent."""
        user_agent = random.choice(settings.BROWSER_USER_AGENTS)
        self.session.headers.update({"User-Agent": user_agent})

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Make GET request with rate limiting.
        
        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments for session.get()
            
        Returns:
            Response object
        """
        rate_limit_wait(
            settings.REQUEST_DELAY_MIN,
            settings.REQUEST_DELAY_MAX,
        )
        
        merged_headers = DEFAULT_HEADERS.copy()
        if headers:
            merged_headers.update(headers)

        logger.debug(f"GET {url} with params {params}")
        
        response = self.session.get(
            url,
            params=params,
            headers=merged_headers,
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Make POST request with rate limiting.
        
        Args:
            url: Request URL
            data: Form data
            json: JSON data
            headers: Additional headers
            **kwargs: Additional arguments for session.post()
            
        Returns:
            Response object
        """
        rate_limit_wait(
            settings.REQUEST_DELAY_MIN,
            settings.REQUEST_DELAY_MAX,
        )
        
        merged_headers = DEFAULT_HEADERS.copy()
        if headers:
            merged_headers.update(headers)

        logger.debug(f"POST {url}")
        
        response = self.session.post(
            url,
            data=data,
            json=json,
            headers=merged_headers,
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def close(self) -> None:
        """Close the session."""
        self.session.close()
        logger.debug("HTTP client session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
