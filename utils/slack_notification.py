import requests
import logging
from typing import Optional, List, Dict, Any
from settings_app.models import SlackToken
from project.models import ProjectSlackChannel

logger = logging.getLogger(__name__)


def send_slack_message(
    channel_id: str,
    message: str,
    blocks: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """
    Send a message to a Slack channel using the stored bot token.
    
    Args:
        channel_id: The Slack channel ID (e.g., 'C123456789')
        message: Plain text message (used as fallback if blocks are provided)
        blocks: Optional Slack Block Kit formatted message blocks
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        # Get the Slack token
        slack_token = SlackToken.objects.first()
        if not slack_token or not slack_token.is_connected:
            logger.warning("Slack is not connected. Cannot send message.")
            return False
        
        headers = {
            'Authorization': f'Bearer {slack_token.slack_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'channel': channel_id,
            'text': message
        }
        
        if blocks:
            payload['blocks'] = blocks
        
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"Slack API error: HTTP {response.status_code}")
            return False
        
        data = response.json()
        if not data.get('ok'):
            logger.error(f"Slack API error: {data.get('error')}")
            return False
        
        logger.info(f"Message sent to Slack channel {channel_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending Slack message: {str(e)}")
        return False


def notify_project_update(project, updated_by, changes: Dict[str, tuple]) -> None:
    """
    Notify all connected Slack channels about a project update.
    
    Args:
        project: The Project instance that was updated
        updated_by: The User who made the update
        changes: Dictionary of field changes in format {field_name: (old_value, new_value)}
    """
    try:
        # Get all Slack channels connected to this project
        project_channels = ProjectSlackChannel.objects.filter(project=project)
        
        if not project_channels.exists():
            logger.debug(f"No Slack channels connected to project {project.name}")
            return
        
        # Helper function to strip HTML tags
        def strip_html(text):
            """Remove HTML tags from text"""
            if not text or text == 'None':
                return text
            import re
            # Remove HTML tags
            clean = re.sub('<.*?>', '', str(text))
            # Clean up extra whitespace
            clean = ' '.join(clean.split())
            return clean
        
        # Build the change description
        change_lines = []
        for field, (old_val, new_val) in changes.items():
            field_display = field.replace('_', ' ').title()
            # Strip HTML from values
            clean_old = strip_html(old_val)
            clean_new = strip_html(new_val)
            change_lines.append(f"• *{field_display}*: {clean_old} → {clean_new}")
        
        changes_text = "\n".join(change_lines)
        
        # Plain text message (fallback)
        plain_message = (
            f"📝 Project Update: {project.name}\n"
            f"Updated by: {updated_by.get_full_name() or updated_by.username}\n"
            f"\nChanges:\n{changes_text}"
        )
        
        # Slack blocks for rich formatting
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📝 Project Update",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{project.name}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Updated by:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{updated_by.get_full_name() or updated_by.username}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{project.status.title()}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Changes:*\n{changes_text}"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Send to all connected channels
        for project_channel in project_channels:
            send_slack_message(
                channel_id=project_channel.channel_id,
                message=plain_message,
                blocks=blocks
            )
            
    except Exception as e:
        logger.error(f"Error notifying project update: {str(e)}")


def notify_project_created(project, created_by) -> None:
    """
    Notify all connected Slack channels about a new project creation.
    
    Args:
        project: The Project instance that was created
        created_by: The User who created the project
    """
    try:
        project_channels = ProjectSlackChannel.objects.filter(project=project)
        
        if not project_channels.exists():
            return
        
        plain_message = (
            f"🚀 New Project Created: {project.name}\n"
            f"Created by: {created_by.get_full_name() or created_by.username}\n"
            f"Priority: {project.priority.title()}\n"
            f"Status: {project.status.title()}\n"
            f"Due Date: {project.due_date if project.due_date else 'Not set'}"
        )
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚀 New Project Created",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:*\n{project.name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Created by:*\n{created_by.get_full_name() or created_by.username}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority:*\n{project.priority.title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{project.status.title()}"
                    }
                ]
            }
        ]
        
        if project.description:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{project.description[:200]}{'...' if len(project.description) > 200 else ''}"
                }
            })
        
        blocks.append({"type": "divider"})
        
        for project_channel in project_channels:
            send_slack_message(
                channel_id=project_channel.channel_id,
                message=plain_message,
                blocks=blocks
            )
            
    except Exception as e:
        logger.error(f"Error notifying project creation: {str(e)}")


def notify_team_member_added(project, added_by, new_member, role) -> None:
    """
    Notify all connected Slack channels when a team member is added to a project.
    
    Args:
        project: The Project instance
        added_by: The User who added the member
        new_member: The User who was added
        role: The role assigned to the new member
    """
    try:
        project_channels = ProjectSlackChannel.objects.filter(project=project)
        
        logger.info(f"Found {project_channels.count()} channels connected to project {project.name}")
        
        if not project_channels.exists():
            logger.warning(f"No Slack channels connected to project {project.name}")
            return
        
        member_name = new_member.get_full_name() or new_member.username
        added_by_name = added_by.get_full_name() or added_by.username
        
        plain_message = (
            f"👥 Team Member Added to {project.name}\n"
            f"{member_name} was added as {role.title()}\n"
            f"Added by: {added_by_name}"
        )
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "👥 Team Member Added",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{project.name}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*New Member:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{member_name}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Role:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{role.title()}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Added by:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{added_by_name}"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        # Send to all connected channels
        for project_channel in project_channels:
            logger.info(f"Sending notification to channel: {project_channel.channel_name} ({project_channel.channel_id})")
            success = send_slack_message(
                channel_id=project_channel.channel_id,
                message=plain_message,
                blocks=blocks
            )
            if success:
                logger.info(f"Successfully sent to {project_channel.channel_name}")
            else:
                logger.error(f"Failed to send to {project_channel.channel_name}")
            
    except Exception as e:
        logger.error(f"Error notifying team member addition: {str(e)}")


def notify_team_member_removed(project, removed_by, removed_member) -> None:
    """
    Notify all connected Slack channels when a team member is removed from a project.
    
    Args:
        project: The Project instance
        removed_by: The User who removed the member
        removed_member: The User who was removed
    """
    try:
        project_channels = ProjectSlackChannel.objects.filter(project=project)
        
        logger.info(f"Found {project_channels.count()} channels connected to project {project.name}")
        
        if not project_channels.exists():
            logger.warning(f"No Slack channels connected to project {project.name}")
            return
        
        member_name = removed_member.get_full_name() or removed_member.username
        removed_by_name = removed_by.get_full_name() or removed_by.username
        
        plain_message = (
            f"👤 Team Member Removed from {project.name}\n"
            f"{member_name} was removed from the project\n"
            f"Removed by: {removed_by_name}"
        )
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "👤 Team Member Removed",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{project.name}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Removed Member:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{member_name}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Removed by:*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{removed_by_name}"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        # Send to all connected channels
        for project_channel in project_channels:
            logger.info(f"Sending notification to channel: {project_channel.channel_name} ({project_channel.channel_id})")
            success = send_slack_message(
                channel_id=project_channel.channel_id,
                message=plain_message,
                blocks=blocks
            )
            if success:
                logger.info(f"Successfully sent to {project_channel.channel_name}")
            else:
                logger.error(f"Failed to send to {project_channel.channel_name}")
            
    except Exception as e:
        logger.error(f"Error notifying team member removal: {str(e)}")
