import time
import requests
import json

class RateLimiter:
    def __init__(self, max_requests, max_tokens):
        self.max_requests = max_requests
        self.max_tokens = max_tokens
        self.remaining_requests = max_requests
        self.remaining_tokens = max_tokens
        self.reset_requests_interval = None
        self.reset_tokens_interval = None

    def wait_until_reset(self):
        now = time.time()
        if self.reset_requests_interval and now < self.reset_requests_interval:
            time.sleep(self.reset_requests_interval - now)
        elif self.reset_tokens_interval and now < self.reset_tokens_interval:
            time.sleep(self.reset_tokens_interval - now)

    def make_request(self, url, method='GET', headers=None, data=None):
        self.wait_until_reset()

        if self.remaining_requests <= 0 or self.remaining_tokens <= 0:
            # If no requests or tokens are left, sleep and reset
            time.sleep(60)
            self.remaining_requests = self.max_requests
            self.remaining_tokens = self.max_tokens

        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, data=json.dumps(data))
        else:
            raise ValueError("Unsupported HTTP method")

        if response.status_code == 429:
            # Rate limit exceeded
            reset_requests = response.headers.get('x-ratelimit-reset-requests')
            reset_tokens = response.headers.get('x-ratelimit-reset-tokens')

            if reset_requests:
                self.reset_requests_interval = time.time() + int(reset_requests[:-1])

            if reset_tokens:
                self.reset_tokens_interval = time.time() + int(reset_tokens[:-1])

            self.wait_until_reset()
            return self.make_request(url, method, headers, data)  # Retry the request

        if response.status_code == 200:
            self.remaining_requests = int(response.headers.get('x-ratelimit-remaining-requests'))
            self.remaining_tokens = int(response.headers.get('x-ratelimit-remaining-tokens'))

        return response
