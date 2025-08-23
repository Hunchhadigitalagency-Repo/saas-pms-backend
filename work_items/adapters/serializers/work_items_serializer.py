from rest_framework import serializers
from django.contrib.auth.models import User
from project.models import Project
from ...models import WorkItems

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name',]

class WorkItemsSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(many=True, read_only=True)
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = WorkItems
        fields = '__all__'