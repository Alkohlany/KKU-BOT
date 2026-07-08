import logging
import json
from datetime import datetime, timezone
from bot.services.database import get_pending_posts, mark_post_published, log_activity
from bot.services.news_publisher import publish_to_groups

logger = logging.getLogger(__name__)


async def check_scheduled_posts(context):
    try:
        pending = await get_pending_posts()
        logger.info(f"Scheduler check: found {len(pending)} pending posts")

        for post in pending:
            try:
                logger.info(f"Publishing scheduled post ID={post.id}: {post.content[:50]}...")
                sent, channel_message_id, group_message_ids = await publish_to_groups(
                    text=post.content,
                    image_url=post.image_url,
                    file_url=post.file_url,
                    to_channel=post.publish_to_channel,
                    as_document=post.as_document,
                    target_channels=post.target_channels
                )
                await mark_post_published(post.id, group_message_ids=json.dumps(group_message_ids) if group_message_ids else None)
                logger.info(f"Published scheduled post ID={post.id}, sent to {sent} groups")
                try:
                    await log_activity(
                        action="scheduled_post_published",
                        details=f"نشر منشور مجدول: {post.content[:50]}...",
                        performed_by=0
                    )
                except Exception as e:
                    logger.warning(f"Failed to log activity: {e}")

                if post.is_recurring and post.recurring_interval:
                    from bot.services.database import reschedule_post
                    await reschedule_post(post.id, post.recurring_interval)
            except Exception as e:
                logger.error(f"Error publishing scheduled post ID={post.id}: {e}")
    except Exception as e:
        logger.error(f"Error in scheduler check: {e}")
