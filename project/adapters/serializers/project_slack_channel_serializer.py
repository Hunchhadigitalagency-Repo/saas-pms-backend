from rest_framework import serializers
from project.models import ProjectSlackChannel


class ProjectSlackChannelSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectSlackChannel model
    """
    class Meta:
        model = ProjectSlackChannel
        fields = ['id', 'project', 'channel_id', 'channel_name', 'is_private', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectSlackChannelDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for ProjectSlackChannel with project info
    """
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = ProjectSlackChannel
        fields = ['id', 'project', 'project_name', 'channel_id', 'channel_name', 'is_private', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
