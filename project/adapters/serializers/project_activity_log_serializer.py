from rest_framework import serializers
from project.models import ProjectActivityLog, Project


class ProjectActivityLogSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectActivityLog model.
    Includes project name and all activity details.
    """
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_id = serializers.IntegerField(source='project.id', read_only=True)
    
    class Meta:
        model = ProjectActivityLog
        fields = ['id', 'project_id', 'project_name', 'activity', 'created_at']
        read_only_fields = ['id', 'created_at', 'project_name', 'project_id']
