from rest_framework import serializers
from project.models import Project, ProjectMembers
from django.contrib.auth.models import User
from user.models import UserProfile


class ProjectUserProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ('profile_picture',)

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

class ProjectMemberUserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'profile')

    def get_profile(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return ProjectUserProfileSerializer(obj.profile, context=self.context).data
        return None

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
    team_members = serializers.ListField(
        child=serializers.JSONField(),
        required=False,
        allow_empty=True
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

    def validate_team_members(self, value):
        """
        Validate and normalize team_members data.
        Accepts both formats:
        - Old format: [1, 2, 3] (just user IDs)
        - New format: [{"user": 1, "role": "member"}, {"user": 2, "role": "owner"}]
        
        Returns normalized format: [{"user": User instance, "role": str}, ...]
        """
        if not value:
            return []
        
        normalized = []
        for item in value:
            # Old format: just an integer (user ID)
            if isinstance(item, int):
                try:
                    user = User.objects.get(pk=item)
                    normalized.append({"user": user, "role": "member"})  # default role
                except User.DoesNotExist:
                    raise serializers.ValidationError(f"User with id {item} does not exist")
            
            # New format: object with user and role
            elif isinstance(item, dict):
                user_id = item.get('user')
                role = item.get('role', 'member')
                
                if not user_id:
                    raise serializers.ValidationError("Each team member must have a 'user' field")
                
                try:
                    user = User.objects.get(pk=user_id)
                    normalized.append({"user": user, "role": role})
                except User.DoesNotExist:
                    raise serializers.ValidationError(f"User with id {user_id} does not exist")
            else:
                raise serializers.ValidationError("Team members must be either user IDs or objects with 'user' and 'role' fields")
        
        return normalized

    def create(self, validated_data):
        team_members_data = validated_data.pop('team_members', [])
        project = Project.objects.create(**validated_data)
        
        for member_data in team_members_data:
            ProjectMembers.objects.create(
                project=project,
                user=member_data['user'],
                role=member_data['role']
            )
        
        return project

    def update(self, instance, validated_data):
        team_members_data = validated_data.pop('team_members', None)
        instance = super().update(instance, validated_data)

        if team_members_data is not None:
            # Track existing members before deletion
            existing_members = {
                member.user.id: {'user': member.user, 'role': member.role}
                for member in instance.projectmembers_set.all()
            }
            
            # Get new members from the data
            new_members_dict = {
                member_data['user'].id: member_data
                for member_data in team_members_data
            }
            
            # Import notification functions
            from utils.slack_notification import notify_team_member_added, notify_team_member_removed
            
            # Check if project has Slack channels connected
            has_slack = instance.slack_channels.exists()
            
            # Get the current user from the context
            request = self.context.get('request')
            current_user = request.user if request else None
            
            # Detect removed members
            if has_slack and current_user:
                for user_id, member_info in existing_members.items():
                    if user_id not in new_members_dict:
                        # Member was removed
                        notify_team_member_removed(instance, current_user, member_info['user'])
            
            # Delete existing members and create new ones
            instance.projectmembers_set.all().delete()
            
            for member_data in team_members_data:
                ProjectMembers.objects.create(
                    project=instance,
                    user=member_data['user'],
                    role=member_data['role']
                )
                
                # Detect newly added members
                if has_slack and current_user and member_data['user'].id not in existing_members:
                    notify_team_member_added(instance, current_user, member_data['user'], member_data['role'])
        
        return instance

class OnGoingProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name']
