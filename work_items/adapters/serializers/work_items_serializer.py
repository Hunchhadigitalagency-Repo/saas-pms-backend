from user.models import UserProfile
from rest_framework import serializers
from django.contrib.auth.models import User
from project.models import Project
from ...models import WorkItems

class WorkItemUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('profile_picture',)

class WorkItemUserSerializer(serializers.ModelSerializer):
    profile = WorkItemUserProfileSerializer()
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'profile')

class WorkItemProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name',]

class WorkItemsSerializer(serializers.ModelSerializer):
    assigned_to = WorkItemUserSerializer(many=True, read_only=True)
    project = WorkItemProjectSerializer(read_only=True)

    class Meta:
        model = WorkItems
        fields = '__all__'

class WorkItemsWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkItems
        fields = (
            'title',
            'description',
            'due_date',
            'status',
            'priority',
            'project',
            'assigned_to',
        )