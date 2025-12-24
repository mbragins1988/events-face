from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class RegisterView(APIView):
    """Регистрация пользователя
    POST /api/auth/register."""

    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        # Проверяем что передали данные
        if not username or not password:
            return Response(
                {"error": "Требуется имя пльзователя и пароль"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем существует ли пользователь
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Создаем пользователя
        user = User.objects.create_user(username=username, password=password)

        # Создаем токены
        refresh = RefreshToken.for_user(user)

        response = Response(
            {
                "message": "User created successfully",
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),  # Новый токен!
            httponly=True,
            max_age=7 * 24 * 60 * 60,
        )

        return response


class LoginView(APIView):
    """Вход пользователя
    POST /api/auth/login."""

    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Invalid username or password"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем логин/пароль
        user = authenticate(username=username, password=password)

        if user is not None:
            # Создаем токены
            refresh = RefreshToken.for_user(user)

            response = Response(
                {
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                }
            )

            response.set_cookie(
                key="refresh_token",
                value=str(str(refresh)),  # Новый токен!
                httponly=True,
                max_age=7 * 24 * 60 * 60,
            )

            return response
        return Response(
            {"error": "Вы не зарегистрированы на сайте!"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class TokenRefreshView(APIView):
    """Механизм обновления токенов с помощью Refresh Token
    POST /api/auth/token/refresh."""

    permission_classes = (AllowAny,)

    def post(self, request):
        if request.data.get("refresh"):
            refresh_token = request.data.get("refresh")
        else:
            # Получаем refresh token из куки
            refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response(
                {"error": "Требуется Refresh токен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)

            # Если ROTATE_REFRESH_TOKENS = True, создается новый refresh
            # Создаем response с новым access_token
            response_data = {"access_token": str(refresh.access_token)}
            response = Response(response_data)

            # Если токен был обновлен (ротация), обновляем куку
            if hasattr(refresh, "refresh_token"):
                response.set_cookie(
                    key="refresh_token",
                    value=str(refresh.refresh_token),  # Новый токен!
                    httponly=True,
                    max_age=7 * 24 * 60 * 60,
                )

            return Response({"access_token": str(refresh.access_token)})
        except TokenError:
            return Response(
                {"error": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    """POST /api/auth/logout."""

    def post(self, request):
        # Получаем refresh token из куки
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response(
                {"error": "Требуется Refresh токен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Добавляем в черный список
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"message": "Вы успешно вышли"})
        except TokenError:
            return Response(
                {"error": "Недействительный или просроченный Refresh токен"},
                status=status.HTTP_400_BAD_REQUEST,
            )
