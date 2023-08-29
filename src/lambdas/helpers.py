import functools
import json
import logging

from datetime import datetime
from time import sleep


def http_response(status_code, status, message):
    body = {
        "status": status,
        "message": message
    }

    return {
        "statusCode": status_code,
        "body": json.dumps(body)
    }


def rate_limit(f):
    """
    Decorator to handle our rate-limit logic.

    In the destination request we keep track of requests per minute. If we exceed
        the requests allowed per minute we pause the remaining time in the minute.
    """
    @functools.wraps(f)
    def rate_limit_wrapper(self, *args, **kwargs):
        if not self.req_per_min:
            return f(self, *args, **kwargs)

        if not self.rate_limit_time_start:
            self.rate_limit_time_start = datetime.now()

        seconds_remaining = (datetime.now() - self.rate_limit_time_start).seconds

        if seconds_remaining <= 60 and self.num_requests > self.req_per_min:
            timeout = 60 - seconds_remaining

            logging.info(f'Exceeded requests per minute. Sleeping: {timeout}')
            sleep(timeout)

        elif seconds_remaining > 60:
            self.rate_limit_time_start = datetime.now()
            self.num_requests = 0

        self.num_requests += 1

        return f(self, *args, **kwargs)

    return rate_limit_wrapper
