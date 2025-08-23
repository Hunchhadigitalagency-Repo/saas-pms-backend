from django.urls import path
from .adapters.viewsets import auth_viewset
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

urlpatterns = [
    # URL for logging in with email
    path('login/email/', auth_viewset.AuthViewSet.as_view({'post': 'login_with_email'}), name='login_email'),
    # URL for logging in with Google
    path('login/google/', auth_viewset.AuthViewSet.as_view({'post': 'login_with_google'}), name='login_google'),
    # URL for user registration
    path('register/', auth_viewset.AuthViewSet.as_view({'post': 'register'}), name='register'),
    # URL for initiating forgot password process
    path('forgot-password/', auth_viewset.AuthViewSet.as_view({'post': 'forgot_password'}), name='forgot_password'),
    # URL for verifying OTP
    path('verify-otp/', auth_viewset.AuthViewSet.as_view({'post': 'verify_otp'}), name='verify_otp'),
    # URL for changing password
    path('change-password/', auth_viewset.AuthViewSet.as_view({'post': 'change_password'}), name='change_password'),
    # URL for logging out
    path('logout/', auth_viewset.AuthViewSet.as_view({'post': 'logout'}), name='logout'),

    # simple jwt verify and refresh api
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # user related to the requested user client
    path('my-client-users/', auth_viewset.ClientViewSet.as_view({'get': 'my_client_users'}), name='my_client_users'),
]
