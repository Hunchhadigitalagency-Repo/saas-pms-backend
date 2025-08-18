from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from customer.models import ActiveClient, Client, Domain, UserClientRole
from ...models import UserProfile



class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]  # applies to all actions in this viewset

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

        # Issue JWT token
        refresh = RefreshToken.for_user(user)

        # Include user profile if exists
        profile = UserProfile.objects.filter(user=user).first()

        response_data = {
            "user": {
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
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)


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
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

