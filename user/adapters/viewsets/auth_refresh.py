from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

COOKIE_DOMAIN = ".pms.hunchhadigital.com.np"

class CookieTokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_cookie = request.COOKIES.get("refresh_token")
        if not refresh_cookie:
            return Response({"detail": "Refresh token cookie missing"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_cookie)
            new_access = str(refresh.access_token)

            res = Response({"detail": "Token refreshed"}, status=status.HTTP_200_OK)
            res.set_cookie(
                key="access_token",
                value=new_access,
                max_age=36000,
                secure=True,
                httponly=True,
                samesite="None",
                path="/",
                domain=COOKIE_DOMAIN,
            )
            return res
        except TokenError:
            return Response({"detail": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
