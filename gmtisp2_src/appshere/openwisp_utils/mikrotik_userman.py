# mpi_src/usermanager/mikrotik_userman.py
import requests
from typing import Optional, List, Dict, Any
import logging
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MikroTikUserManager:
    def __init__(self, router_ip: str, router_username: str, router_password: str):
        self.router_ip = router_ip.rstrip('/')
        self.session = requests.Session()
        self.session.auth = (router_username, router_password)
        self.session.headers.update({'Content-Type': 'application/json'})

    # @retry(
    #     wait=wait_fixed(3),  # Wait 3 seconds between retries
    #     stop=stop_after_attempt(5),  # Stop after 5 attempts
    #     retry=retry_if_exception_type((requests.exceptions.RequestException,))
    # )
    def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.router_ip}/{endpoint.lstrip('/')}"
        try:
            logger.info(f"{method.upper()} request to {url} with data: {data}")
            response = self.session.request(method=method.upper(), url=url, json=data, timeout=10)
            response.raise_for_status()
            return response.json() if response.content else None
        except:
            pass
        # except requests.exceptions.HTTPError as http_err:
        #     # Log detailed error response for debugging 400 errors
        #     if response.status_code == 400:
        #         logger.error(f"400 Bad Request: {response.text}")
        #     else:
        #         logger.error(f"HTTP error {response.status_code} for {url}: {response.text}")
        #     raise
        # except requests.exceptions.RequestException as req_err:
        #     logger.error(f"Request exception for {url}: {req_err}")
        #     raise

    # ------------------------------------------------ users
    def get_users(self) -> List[Dict[str, Any]]:
        return self._request('GET', 'rest/user-manager/user') or []

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._request('GET', f'rest/user-manager/user/{user_id}')

    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('PUT', 'rest/user-manager/user', data=user_data)

    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._request('PATCH', f'rest/user-manager/user/{user_id}', data=user_data)

    def delete_user(self, user_id: str) -> None:
        self._request('DELETE', f'rest/user-manager/user/{user_id}')

    # -- user usage
    def monitor_user_usage(self, user_id: str) -> Optional[Dict[str, Any]]:
        data = {"once": True, ".id": user_id}

        try:
            return self._request('POST', 'rest/user-manager/user/monitor', data=data)
        except Exception as e:
            logger.error(f"Error monitoring usage for user '{user_id}': {e}")
            raise RuntimeError(f"Error monitoring usage for user '{user_id}': {e}")
        
    # ------------------------------------------------ profiles
    def get_profiles(self) -> List[Dict[str, Any]]:
        return self._request('GET', 'rest/user-manager/profile') or []

    def create_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('PUT', 'rest/user-manager/profile', data=profile_data)

    def update_profile(self, profile_id: str, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._request('PATCH', f'rest/user-manager/profile/{profile_id}', data=profile_data)

    def delete_profile(self, profile_id: str) -> None:
        self._request('DELETE', f'rest/user-manager/profile/{profile_id}')

    # ------------------------------------------------ user profiles
    def get_user_profiles(self) -> List[Dict[str, Any]]:
        return self._request('GET', 'rest/user-manager/user-profile') or []

    def get_user_profile(self, user_profile_id: str) -> Optional[Dict[str, Any]]:
        return self._request('GET', f'rest/user-manager/user-profile/{user_profile_id}')

    def create_user_profile(self, user_profile_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('PUT', 'rest/user-manager/user-profile', data=user_profile_data)

    def update_user_profile(self, user_profile_id: str, user_profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._request('PATCH', f'rest/user-manager/user-profile/{user_profile_id}', data=user_profile_data)

    def delete_user_profile(self, user_profile_id: str) -> None:
        self._request('DELETE', f'rest/user-manager/user-profile/{user_profile_id}')

    # ------------------------------------------------ limitation
    def get_limitations(self) -> List[Dict[str, Any]]:
        return self._request('GET', 'rest/user-manager/limitation') or []

    def create_limitation(self, limitation_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('PUT', 'rest/user-manager/limitation', data=limitation_data)

    def update_limitation(self, limitation_id: str, limitation_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._request('PATCH', f'rest/user-manager/limitation/{limitation_id}', data=limitation_data)

    def delete_limitation(self, limitation_id: str) -> None:
        self._request('DELETE', f'rest/user-manager/limitation/{limitation_id}')

    # ------------------------------------------------ profile limitation
    def get_profile_limitations(self) -> List[Dict[str, Any]]:
        return self._request('GET', 'rest/user-manager/profile-limitation') or []

    def create_profile_limitation(self, profile_limitation_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('PUT', 'rest/user-manager/profile-limitation', data=profile_limitation_data)

    def update_profile_limitation(self, profile_limitation_id: str, profile_limitation_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._request('PATCH', f'rest/user-manager/profile-limitation/{profile_limitation_id}', data=profile_limitation_data)

    def delete_profile_limitation(self, profile_limitation_id: str) -> None:
        self._request('DELETE', f'rest/user-manager/profile-limitation/{profile_limitation_id}')

    # ------------------------------------------------ payments
    def get_payments(self) -> List[Dict[str, Any]]:
        return self._request('GET', 'rest/user-manager/payment') or []

    def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        return self._request('GET', f'rest/user-manager/payment/{payment_id}')

    def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('PUT', 'rest/user-manager/payment', json=payment_data)

    def update_payment(self, payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('PATCH', f'rest/user-manager/payment/{payment_id}', json=update_data)

    def delete_payment(self, payment_id: str) -> None:
        self._request('DELETE', f'rest/user-manager/payment/{payment_id}')

    # ------------------------------------------------ sessions
    def get_sessions(self) -> List[Dict[str, Any]]:
        return self._request('GET', 'rest/user-manager/session') or []

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._request('GET', f'rest/user-manager/session/{session_id}')

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        sessions = self.get_sessions()
        return [session for session in sessions if session.get('user') == user_id]

    def delete_session(self, session_id: str) -> None:
        self._request('DELETE', f'rest/user-manager/session/{session_id}')


# Initialize the MikroTik manager
from django.conf import settings
def init_mikrotik_manager():
    return MikroTikUserManager(
        router_ip=settings.ROUTER_IP,
        router_username=settings.ROUTER_USERNAME,
        router_password=settings.ROUTER_PASSWORD
    )

