from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    """Для регистрации"""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
