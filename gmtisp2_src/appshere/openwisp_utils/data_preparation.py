# mpi_src/usermanager/data_preparation.py
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_uptime_limit(value: str) -> str:
    if not value:
        return ''
    parts = value.split()
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        days, time_str = parts[0], parts[1]
        time_parts = time_str.split(':')
        return f"{days}d {time_parts[0]}:{time_parts[1]}:{time_parts[2]}"
    return value


# def prepare_user_data(user) -> dict:
#     mikrotik_id = user.mikrotik_id or f"*{user.id}"
#     return {
#         '.id': mikrotik_id,
#         'name': user.username or '',
#         'password': user.plain_password or '',
#         'group': user.group or '',
#         'shared-users': str(user.shared_users or '1'),
#         'disabled': str(user.disabled).lower(),
#         'attributes': user.attributes or '',
#         'otp-secret': user.otp_secret or '',
#     }
# Adjust `prepare_user_data` to exclude '.id' when creating new users
def prepare_user_data(user, is_update: bool = False) -> dict:
    """Prepare user data for MikroTik, excluding '.id' if it's a new user."""
    user_data = {
        'name': user.username or '',
        'password': user.plain_password or '',
        'group': user.group or 'default',
        'shared-users': str(user.shared_users or '1'),
        'disabled': str(user.disabled).lower(),
        'attributes': user.attributes or '',
        'otp-secret': user.otp_secret or '',
    }
    # Include '.id' only if updating
    if is_update and user.mikrotik_id:
        user_data['.id'] = user.mikrotik_id
    logger.debug(f"Prepared user data (is_update={is_update}): {user_data}")
    return user_data

def prepare_profile_data(profile) -> dict:
    return {
        # '.id': profile.mikrotik_id or f"*{profile.id}",
        'name': profile.name or '',
        'name-for-users': profile.name_for_users or '',
        'price': str(profile.price or ''),
        'starts-when': profile.starts_when or '',
        'validity': profile.validity or '',
        'override-shared-users': profile.override_shared_users or '',
    }


def prepare_user_profile_data(user_profile) -> dict:
    """Prepare user profile data for MikroTik with serializable values."""
    return {
        # '.id': user_profile.mikrotik_id or f"*{user_profile.id}",
        'user': user_profile.user.mikrotik_id if user_profile.user else '',  # Ensure user ID is used
        'profile': user_profile.profile.mikrotik_id if user_profile.profile else '',  # Ensure profile ID is used
        # 'state': user_profile.state or '',
        # 'end-time': user_profile.end_time or '',
    }


def prepare_limitation_data(limitation) -> dict:
    formatted_uptime_limit = format_uptime_limit(limitation.uptime_limit)
    return {
        # '.id': limitation.mikrotik_id or f"*{limitation.id}",
        'name': limitation.name or '',
        'download-limit': limitation.download_limit or '',
        'upload-limit': limitation.upload_limit or '',
        'transfer-limit': limitation.transfer_limit or '',
        'uptime-limit': formatted_uptime_limit,
        'rate-limit-rx': limitation.rate_limit_rx or '',
        'rate-limit-tx': limitation.rate_limit_tx or '',
        'rate-limit-min-rx': limitation.rate_limit_min_rx or '',
        'rate-limit-min-tx': limitation.rate_limit_min_tx or '',
        'rate-limit-priority': limitation.rate_limit_priority or '',
        'rate-limit-burst-rx': limitation.rate_limit_burst_rx or '',
        'rate-limit-burst-tx': limitation.rate_limit_burst_tx or '',
        'rate-limit-burst-threshold-rx': limitation.rate_limit_burst_threshold_rx or '',
        'rate-limit-burst-threshold-tx': limitation.rate_limit_burst_threshold_tx or '',
        'rate-limit-burst-time-rx': limitation.rate_limit_burst_time_rx or '',
        'rate-limit-burst-time-tx': limitation.rate_limit_burst_time_tx or '',
        'reset-counters-start-time': limitation.reset_counters_start_time or '',
        'reset-counters-interval': limitation.reset_counters_interval or '',
    }


def prepare_profile_limitation_data(profile_limitation) -> dict:
    """Prepare profile limitation data for MikroTik, ensuring all fields are JSON-serializable."""
    return {
        # '.id': profile_limitation.mikrotik_id or f"*{profile_limitation.id}",
        'profile': profile_limitation.profile.mikrotik_id if profile_limitation.profile else '',  # Use Profile's MikroTik ID
        'limitation': profile_limitation.limitation.mikrotik_id if profile_limitation.limitation else '',  # Use Limitation's MikroTik ID
        'from-time': profile_limitation.from_time or '00:00:00',
        'till-time': profile_limitation.till_time or '23:59:59',
        # 'weekdays': profile_limitation.weekdays or '',
    }


def prepare_session_data(session) -> dict:
    return {
        '.id': session.mikrotik_id or f"*{session.id}",
        'acct-session-id': session.acct_session_id or '',
        'active': str(session.active).lower(),
        'calling-station-id': session.calling_station_id or '',
        'download': session.download or '',
        'ended': session.ended or '',
        'last-accounting-packet': session.last_accounting_packet or '',
        'nas-ip-address': session.nas_ip_address or '',
        'nas-port-id': session.nas_port_id or '',
        'nas-port-type': session.nas_port_type or '',
        'started': session.started or '',
        'status': session.status or '',
        'terminate-cause': session.terminate_cause or '',
        'upload': session.upload or '',
        'uptime': session.uptime or '',
        'user': session.user or '',
        'user-address': session.user_address or '',
    }
