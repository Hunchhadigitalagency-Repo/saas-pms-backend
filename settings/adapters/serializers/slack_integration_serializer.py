from rest_framework import serializers
from settings.models import SlackToken


class SlackTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlackToken
        fields = ['id', 'slack_token', 'team_id', 'team_name', 'is_connected', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'slack_token': {'write_only': True}  # Don't expose token in responses
        }


class SlackTokenDetailSerializer(serializers.ModelSerializer):
    is_connected = serializers.SerializerMethodField()

    class Meta:
        model = SlackToken
        fields = ['is_connected', 'team_name', 'team_id']
        read_only_fields = ['is_connected', 'team_name', 'team_id']

    def get_is_connected(self, obj):
        return obj.is_connected and obj.slack_token is not None
