import logging

import requests
from requests.adapters import HTTPAdapter, Retry

from app.config import config

logger = logging.getLogger(__name__)


def get_user_groups(sciper):
    url = f"{config.get('epfl groups', {}).get('host')}:{config.get('epfl groups', {}).get('port')}"
    url += f'/v1/groups?pagesize=0&member={sciper}'
    auth = (config.get('epfl groups', {}).get('username'), config.get('epfl groups', {}).get('password'))

    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504], raise_on_status=False)

    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        response = session.get(url, auth=auth, timeout=10)

        if not response.ok:
            logger.warning(f"Failed to fetch groups for {sciper}: HTTP {response.status_code}")
            return []

        data = response.json()
        return [group['name'] for group in data.get('groups', [])]
    except requests.RequestException as e:
        # This catches connection errors, timeouts, etc.
        logger.warning(f"Error fetching groups for {sciper}: {e}")
        return []
    except ValueError:
        # This catches JSON decoding errors
        logger.warning(f"Invalid JSON received for {sciper}")
        return []


if __name__ == '__main__':
    groups = get_user_groups(157873)
    print(len(groups), groups)
