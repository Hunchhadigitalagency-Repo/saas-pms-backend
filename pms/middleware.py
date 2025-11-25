"""
Debug middleware to log authentication and cookie information.
"""
import logging

logger = logging.getLogger(__name__)


class DebugAuthenticationMiddleware:
    """
    Middleware to log authentication and cookie details for debugging.
    Remove or disable in production.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log cookie presence for authenticated endpoints
        if 'my-client-users' in request.path or 'projects' in request.path:
            access_token = request.COOKIES.get('access_token')
            refresh_token = request.COOKIES.get('refresh_token')
            user = request.user
            
            logger.info(
                f"Request to {request.path}: "
                f"has_access_token={bool(access_token)}, "
                f"has_refresh_token={bool(refresh_token)}, "
                f"user_authenticated={user.is_authenticated}, "
                f"user_id={getattr(user, 'id', None)}"
            )

        response = self.get_response(request)
        return response
