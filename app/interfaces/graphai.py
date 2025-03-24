import time

import requests

from app.config import config


class GraphAIClient:

    def __init__(self):
        self.url = f"{config['graphai']['host']}"
        self.username = config['graphai']['username']
        self.password = config['graphai']['password']

        self.bearer_token = None

    def authenticate(self):
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'grant_type': '',
            'username': self.username,
            'password': self.password,
            'scope': '',
            'client_id': '',
            'client_secret': '',
        }
        result = requests.post(f'{self.url}/token', headers=headers, data=data).json()

        try:
            self.bearer_token = result['access_token']
        except KeyError:
            print(result)

    def call_async_endpoint(self, endpoint, payload, timeout=10, verbose=False):

        # Make sure we are authenticated
        self.authenticate()

        headers = {'Authorization': f'Bearer {self.bearer_token}'}

        # Make first request, which will return a task_id
        response = requests.post(f'{self.url}{endpoint}', headers=headers, json=payload).json()

        if verbose:
            print(response)

        # Extract task_id to poll for result
        task_id = response['task_id']

        # Poll for result until timeout is reached
        limit_time = time.time() + timeout
        while True:
            response = requests.get(f'{self.url}{endpoint}/status/{task_id}', headers=headers).json()

            if verbose:
                print(response)

            # If result is available, return it
            if response['task_result'] is not None:
                return response['task_result']

            # If status is FAILURE, return immediately because some problem happened
            if response['task_status'] == 'FAILURE':
                print(response)
                return None

            # Stop if timeout is reached
            if time.time() > limit_time:
                print(f'Timeout reached for payload {payload}')
                break

            # Wait before next iteration
            time.sleep(1)

        return None

    def call_sync_endpoint(self, endpoint, payload, timeout=10, verbose=False):

        # Make sure we are authenticated
        self.authenticate()

        headers = {'Authorization': f'Bearer {self.bearer_token}'}

        # Make first request, which will return a task_id
        response = requests.post(f'{self.url}{endpoint}', headers=headers, json=payload, timeout=timeout).json()

        if verbose:
            print(response)

        return response
