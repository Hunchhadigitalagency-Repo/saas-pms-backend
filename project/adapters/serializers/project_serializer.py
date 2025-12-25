from rest_framework import serializers
from project.models import Project, ProjectMembers
from django.contrib.auth.models import User
from user.models import UserProfile


class ProjectUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('profile_picture',)

class ProjectMemberUserSerializer(serializers.ModelSerializer):
    profile = ProjectUserProfileSerializer()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'profile')

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

class ProjectWriteSerializer(serializers.ModelSerializer):
    team_members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False
    )

    class Meta:
        model = Project
        fields = (
            'name',
            'description',
            'due_date',
            'status',
            'priority',
            'meeting_link',
            'team_members',
        )

    def create(self, validated_data):
        team_members_data = validated_data.pop('team_members', [])
        project = Project.objects.create(**validated_data)
        for member in team_members_data:
            ProjectMembers.objects.create(project=project, user=member)
        return project

    def update(self, instance, validated_data):
        team_members_data = validated_data.pop('team_members', None)
        instance = super().update(instance, validated_data)

        if team_members_data is not None:
            instance.projectmembers_set.all().delete()
            for member in team_members_data:
                ProjectMembers.objects.create(project=instance, user=member)
        return instance

class OnGoingProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name']
