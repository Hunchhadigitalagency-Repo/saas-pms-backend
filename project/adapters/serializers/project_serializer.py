from rest_framework import serializers
from project.models import Project, ProjectMembers
from django.contrib.auth.models import User

class ProjectMemberUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class ProjectMemberSerializer(serializers.ModelSerializer):
    user = ProjectMemberUserSerializer(read_only=True)

    class Meta:
        model = ProjectMembers
        fields = ('user', 'role')

class ProjectSerializer(serializers.ModelSerializer):
    team_members = ProjectMemberSerializer(source='projectmembers_set', many=True, read_only=True)

    class Meta:
        model = Project
        fields = '__all__'

class OnGoingProjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Project
        fields = ['id', 'name']