# mpi_src/appshere/billings/signals.py
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.timezone import now

from .tasks import trigger_mikrotik_tasks
from .models import User, Profile, UserProfile, Limitation, ProfileLimitation, Payment, Session
from utils.mikrotik_userman import init_mikrotik_manager

mikrotik_manager = init_mikrotik_manager()
logger = logging.getLogger(__name__)


# General signal handler for post_save
@receiver(post_save, sender=User)
@receiver(post_save, sender=Profile)
@receiver(post_save, sender=UserProfile)
@receiver(post_save, sender=Limitation)
@receiver(post_save, sender=ProfileLimitation)
def trigger_mikrotik_task_on_save(sender, instance, created, **kwargs):
    trigger_mikrotik_tasks(instance, created, **kwargs)


# # General signal handler for post_delete
# @receiver(post_delete, sender=User)
# @receiver(post_delete, sender=Profile)
# @receiver(post_delete, sender=UserProfile)
# @receiver(post_delete, sender=Limitation)
# @receiver(post_delete, sender=ProfileLimitation)
# def trigger_delete_mikrotik_task_on_delete(sender, instance, **kwargs):
#     trigger_delete_mikrotik_tasks(instance, **kwargs)


# signal handler for post_delete
@receiver(post_delete, sender=User)
def delete_user_signal(sender, instance, **kwargs):
    """Delete user from MikroTik when the user is deleted in Django."""
    if instance.mikrotik_id:
        try:
            existing_user = next(
                (u for u in mikrotik_manager.get_users() if u['name'] == instance.username), None
            )
            if existing_user:
                mikrotik_manager.delete_user(user_id=existing_user['.id'])
                logger.info(f'Deleted user {instance.username} from MikroTik.')
            else:
                logger.warning(f'User {instance.username} does not exist in MikroTik.')
        except Exception as e:
            logger.error(f'Error deleting user {instance.username} from MikroTik: {e}', exc_info=True)

@receiver(post_delete, sender=Profile)
def delete_profile_signal(sender, instance, **kwargs):
    """Delete profile from MikroTik when the profile is deleted in Django."""
    if instance.mikrotik_id:
        try:
            existing_profile = next(
                (p for p in mikrotik_manager.get_profiles() if p['name'] == instance.name), None
            )
            if existing_profile:
                mikrotik_manager.delete_profile(profile_id=existing_profile['.id'])
                logger.info(f'Deleted profile {instance.name} from MikroTik.')
            else:
                logger.warning(f'Profile {instance.name} does not exist in MikroTik.')
        except Exception as e:
            logger.error(f'Error deleting profile {instance.name} from MikroTik: {e}', exc_info=True)

@receiver(post_delete, sender=UserProfile)
def delete_user_profile_signal(sender, instance, **kwargs):
    """Delete user profile from MikroTik when the user profile is deleted in Django."""
    if instance.mikrotik_id:
        try:
            existing_user_profile = next(
                (up for up in mikrotik_manager.get_user_profiles() if up['user'] == instance.user.username), None
            )
            if existing_user_profile:
                mikrotik_manager.delete_user_profile(user_profile_id=existing_user_profile['.id'])
                logger.info(f'Deleted user profile for {instance.user.username} from MikroTik.')
            else:
                logger.warning(f'User profile for {instance.user.username} does not exist in MikroTik.')
        except Exception as e:
            logger.error(f'Error deleting user profile for {instance.user.username} from MikroTik: {e}', exc_info=True)

@receiver(post_delete, sender=Limitation)
def delete_limitation_signal(sender, instance, **kwargs):
    """Delete limitation from MikroTik when the limitation is deleted in Django."""
    if instance.mikrotik_id:
        try:
            existing_limitation = next(
                (l for l in mikrotik_manager.get_limitations() if l['name'] == instance.name), None
            )
            if existing_limitation:
                mikrotik_manager.delete_limitation(limitation_id=existing_limitation['.id'])
                logger.info(f'Deleted limitation {instance.name} from MikroTik.')
            else:
                logger.warning(f'Limitation {instance.name} does not exist in MikroTik.')
        except Exception as e:
            logger.error(f'Error deleting limitation {instance.name} from MikroTik: {e}', exc_info=True)

@receiver(post_delete, sender=ProfileLimitation)
def delete_profile_limitation_signal(sender, instance, **kwargs):
    """Delete profile limitation from MikroTik when the profile limitation is deleted in Django."""
    if instance.mikrotik_id:
        try:
            existing_profile_limitation = next(
                (pl for pl in mikrotik_manager.get_profile_limitations() if pl['profile'] == instance.profile.name), None
            )
            if existing_profile_limitation:
                mikrotik_manager.delete_profile_limitation(limitation_id=existing_profile_limitation['.id'])
                logger.info(f'Deleted profile limitation for {instance.profile.name} from MikroTik.')
            else:
                logger.warning(f'Profile limitation for {instance.profile.name} does not exist in MikroTik.')
        except Exception as e:
            logger.error(f'Error deleting profile limitation for {instance.profile.name} from MikroTik: {e}', exc_info=True)

@receiver(post_delete, sender=Session)
def delete_session_signal(sender, instance, **kwargs):
    """Delete session from MikroTik when a Session is deleted in Django."""
    if instance.mikrotik_id:
        try:
            existing_session = next(
                (session for session in mikrotik_manager.get_sessions() if session['acct-session-id'] == instance.session_id), None
            )

            if existing_session:
                # Delete the session from MikroTik
                mikrotik_manager.delete_session(session_id=existing_session['.id'])
                logger.info(f'Deleted session {instance.session_id} from MikroTik.')
            else:
                logger.warning(f'Session {instance.session_id} does not exist in MikroTik.')
        
        except Exception as e:
            logger.error(f'Error deleting session {instance.session_id} from MikroTik: {e}', exc_info=True)
    else:
        logger.warning(f'Session {instance.session_id} does not have a MikroTik session ID.')


# # create payment object when user is assigned to a profile
# @receiver(post_save, sender=UserProfile)
# def create_payment_on_profile_assignment(sender, instance, created, **kwargs):
#     if instance.profile:
#         # Check if it's a new instance or if a specific field has changed
#         if created or instance.profile != instance.__class__.objects.get(pk=instance.pk).profile:
#             Payment.objects.create(
#                 user_profile=instance,
#                 user=instance.user,  # Assuming `UserProfile` has a reference to `User`
#                 organization=instance.user.organization, 
#                 copy_from='manual',
#                 method='OFFLINE',
#                 profile=instance.profile,
#                 trans_start=now(),
#                 trans_status='completed',
#                 user_message='Offline Payment created upon profile assignment.',
#                 currency='GHS',
#                 price=instance.profile.price,
#                 trans_end=now()
#             )



# # assign user profile for a user upon successfull/completed payment
# @receiver(post_save, sender=Payment)
# def create_user_profile_upon_payment_completion_signal(sender, instance, created, **kwargs):
#     from .tasks import create_or_update_user_profile_event

#     if not created:
#         return  # Only process newly created Payment instances

#     try:
#         # Log payment creation
#         logger.info(f"Signal triggered for Payment ID: {instance.id}, Status: {instance.trans_status}, User ID: {instance.user.id if instance.user else 'No User'}")

#         # Proceed only if the payment was successful and status is 'completed'
#         if instance.trans_status == 'completed':
#             # Check if user_profile exists
#             if hasattr(instance, 'user_profile') and instance.user_profile:
#                 # Trigger the user profile update function
#                 create_or_update_user_profile_event(instance.user_profile.id)
#                 logger.info(f"Triggered create_user_profile_event for UserProfile ID: {instance.user_profile.id}")
#             else:
#                 logger.warning(f"Payment ID {instance.id} has no associated user profile.")
#         else:
#             logger.warning(f"Payment ID {instance.id} has not completed successfully. Status: {instance.trans_status}")
    
#     except Exception as e:
#         logger.error(f"Error in payment signal for Payment ID {instance.id}: {e}", exc_info=True)
