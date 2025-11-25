"""
Custom JWT authentication that reads tokens from cookies instead of Authorization headers.
This is more secure as it prevents XSS attacks from stealing tokens.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.http import HttpRequest
from typing import Tuple, Optional


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads access tokens from HttpOnly cookies.
    Falls back to Authorization header for backward compatibility (e.g., testing, mobile apps).
    
    Cookie tokens are more secure because:
    - They cannot be accessed by JavaScript (HttpOnly flag)
    - CSRF protection is built-in (SameSite flag)
    - Browser manages them automatically
    """

    def authenticate(self, request: HttpRequest) -> Optional[Tuple]:
        """
        Authenticate by looking for JWT token in cookies first, then headers.
        
        Args:
            request: The HTTP request
            
        Returns:
            A tuple of (user, validated_token) if authentication succeeds
            None if no credentials are provided
            Raises AuthenticationFailed if credentials are invalid
        """
        # Try to get token from cookies first (secure method)
        access_token = request.COOKIES.get('access_token')
        
        if access_token is None:
            # Fall back to Authorization header for backward compatibility
            # This allows testing tools and mobile apps to work
            return super().authenticate(request)

        # Validate the token
        try:
            validated_token = self.get_validated_token(access_token)
        except AuthenticationFailed:
            # Token is invalid, re-raise the exception
            raise

        return self.get_user(validated_token), validated_token

    def authenticate_header(self, request: HttpRequest) -> str:
        """
        Return a string to be used as the value of the `WWW-Authenticate` header
        in a `401 Unauthenticated` response.
        """
        return 'Bearer'
