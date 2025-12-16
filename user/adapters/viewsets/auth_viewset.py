from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from ..serializers.user_serializers import UserSerializer, LoginSerializer
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from django.contrib.auth.models import User
from customer.models import ActiveClient, Client, Domain, UserClientRole
from ...models import UserProfile



class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]  # applies to all actions in this viewset
    serializer_class = LoginSerializer

    @action(detail=False, methods=["post"])
    def login_with_email(self, request):
        print("Login with email called")
        email = request.data.get("email")
        password = request.data.get("password")

        print(f"Login attempt with email: {email}")
        print(f"Password provided: {'*' * len(password) if password else 'None'}")

        if not email or not password:
            return Response(
                {"error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find user by email
        find_user = User.objects.filter(email=email).first()
        if not find_user:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Authenticate user
        user = authenticate(request, username=find_user.username, password=password)
        print(f"User authenticated: {user}")
        if not user:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            # Get user's active client
            active_client_entry = ActiveClient.objects.filter(user=user).first()
            if not active_client_entry:
                return Response(
                    {"error": "No active client found for this user"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            client = Client.objects.filter(id=active_client_entry.client.id).first()
            if not client:
                return Response(
                    {"error": "Client not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get the primary domain (or first domain)
            domain = Domain.objects.filter(tenant=client).first()
            if not domain:
                return Response(
                    {"error": "Domain for client not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get the user's role for this client
            user_role_entry = UserClientRole.objects.filter(user=user, client=client).first()
            user_role = user_role_entry.role if user_role_entry else None

        except Exception as e:
            print(f"Error fetching client/domain/role: {e}")
            return Response(
                {"error": "Client for this user could not be found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Include user profile if exists
        profile = UserProfile.objects.filter(user=user).first()

        # Prepare response data (NO TOKENS IN BODY - they'll be in cookies)
        response_data = {
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "profile": {
                "profile_picture": profile.profile_picture.url if profile and profile.profile_picture else None,
            } if profile else None,
            "client": {
                "name": client.name,
                "schema_name": client.schema_name,
            },
            "domains": {
                "domain": domain.domain,
                "is_primary": domain.is_primary,
            },
            "user_role": user_role,
            # NOTE: Tokens are NOT returned in response body
            # They are set as HttpOnly cookies by the response object below
        }

        
        # Create response
        response = Response(response_data, status=status.HTTP_200_OK)

        # Set tokens as HttpOnly cookies (more secure than localStorage)
        # These cookies cannot be accessed by JavaScript (prevents XSS theft)
        response.set_cookie(
            key='access_token',
            value=access_token,
            max_age=36000,  # 10 hours (match SIMPLE_JWT ACCESS_TOKEN_LIFETIME)
            secure=True,
            httponly=True,  # Not accessible from JavaScript
            samesite='None',
            path='/',
            domain=None,
        )

        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            max_age=604800,  # 7 days (match SIMPLE_JWT REFRESH_TOKEN_LIFETIME)
            secure=True,
            httponly=True,
            samesite='None',
            path='/',
            domain=None,
        )

        return response


    def login_with_google(self, request, *args, **kwargs):
        # Implement Google login logic here
        pass

    def register(self, request, *args, **kwargs):
        # Implement registration logic here
        pass

    def forgot_password(self, request, *args, **kwargs):
        return auth_views.PasswordResetView.as_view(
            success_url=reverse_lazy('password_reset_done')
        )(request, *args, **kwargs)

    def verify_otp(self, request, *args, **kwargs):
        # Implement OTP verification logic here
        pass

    def change_password(self, request, *args, **kwargs):
        return auth_views.PasswordChangeView.as_view(
            success_url=reverse_lazy('password_change_done')
        )(request, *args, **kwargs)

    def logout(self, request, *args, **kwargs):
        """
        Logout user by clearing HttpOnly cookies.
        No database blacklist needed since tokens are just deleted.
        """
        # Detect environment based on request origin (same logic as login)
        origin = request.META.get('HTTP_ORIGIN', '')
        is_localhost = 'localhost' in origin or '127.0.0.1' in origin
        
        # Use same domain as login
        cookie_domain = None if is_localhost else '.pms.hunchhadigital.com.np'
        
        response = Response(
            {"message": "Successfully logged out"},
            status=status.HTTP_200_OK
        )
        
        # Clear the authentication cookies (with matching domain and samesite)
        response.delete_cookie(
            'access_token',
            path='/',
            domain=cookie_domain,
            samesite='Lax' if is_localhost else 'None'
        )
        response.delete_cookie(
            'refresh_token',
            path='/',
            domain=cookie_domain,
            samesite='Lax' if is_localhost else 'None'
        )
        
        return response

class ClientViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]  # Allow anonymous initially, authenticate inside the view

    @extend_schema(
        summary="Get users associated with the authenticated user's active client",
        description="Retrieves a list of all users who are part of the same active client as the authenticated user.",
        responses={
            200: UserSerializer(many=True)
        }
    )
    def my_client_users(self, request, *args, **kwargs):
        """
        Authenticate user from cookie JWT and return users in their active client.
        If not authenticated, tries to manually extract and validate token from cookie.
        """
        user = request.user
        
        # If user is not authenticated, try to manually authenticate from cookie
        if user.is_anonymous:
            try:
                from pms.jwt_auth import CookieJWTAuthentication
                auth = CookieJWTAuthentication()
                result = auth.authenticate(request)
                
                if result is not None:
                    user, validated_token = result
                    request.user = user
                    print(f"Successfully authenticated user {user.id} from cookie")
                else:
                    print("No authentication result from cookie JWT auth")
                    return Response(
                        {"detail": "Authentication credentials were not provided."},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            except Exception as e:
                print(f"Failed to authenticate from cookie: {type(e).__name__}: {e}")
                return Response(
                    {"detail": "Authentication credentials were not provided."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # After authentication, check if user is still anonymous
        if user.is_anonymous:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get user's active client and associated users
        try:
            user_active_client = ActiveClient.objects.filter(user=user).first()
            if not user_active_client:
                return Response(
                    {"error": "No active client found for this user"},
                    status=status.HTTP_404_NOT_FOUND
                )

            users_in_this_client = UserClientRole.objects.filter(
                client=user_active_client.client
            ).select_related('user')
            client_users = [user_role.user for user_role in users_in_this_client]

            serializer = UserSerializer(client_users, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error fetching client users: {type(e).__name__}: {e}")
            return Response(
                {"error": "Failed to fetch client users"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
