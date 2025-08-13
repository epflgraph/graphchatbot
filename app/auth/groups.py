import requests

from app.config import config


def get_user_groups(sciper):
    url = f'https://api.epfl.ch/v1/groups?pagesize=0&member={sciper}'
    auth = (config.get('epfl groups', {}).get('username'), config.get('epfl groups', {}).get('password'))

    response = requests.get(url, auth=auth).json()

    groups = [group['name'] for group in response['groups']]

    return groups


if __name__ == '__main__':
    groups = get_user_groups(157873)
    print(len(groups), groups)
