import re
from typing import List
from urllib.parse import urlparse

from playwright.sync_api import Page, Request

from util import config
from util.get_logger import get_logger

logger = get_logger(__name__)


class PageLoader:
    network_idle_time = config.get('network_idle_time')
    request_wait_url_pattern = config.get('network_idle_requests_url_pattern')
    network_idle_ignore_pattern = config.get('network_idle_ignore_pattern')
    network_idle_check = config.get('network_idle_check')
    requests: List[str] = []

    def __init__(self, page: Page, url: str):
        self.page = page
        self.url = url
        self.pending_requests = 0
        base_url_pattern = re.escape(self._base_url(url))
        self.request_wait_url_pattern = self.request_wait_url_pattern.replace('@BASE_URL@', base_url_pattern)

        if self.network_idle_check:
            self._attach_handlers(True)
            pass

        pass

    def _attach_handlers(self, attach: bool):
        logger.debug('_attach_handlers: attach=%s', attach)

        if attach:
            fun = self.page.on
        else:
            fun = self.page.remove_listener
            pass

        event_map = [
            'request',
            'requestfinished',
            'requestfailed'
        ]

        for i in event_map:
            if i == 'request':
                handler = self._handle_request
            else:
                handler = self._handle_response
                pass
            fun(i, handler)
            pass
        pass

    def _handle_request(self, request: Request):
        self._request_handler(request, 1)
        pass

    def _handle_response(self, request: Request):
        self._request_handler(request, -1)
        pass

    def _request_handler(self, request: Request, incr: int):
        if re.match(
                self.network_idle_ignore_pattern,
                request.url
        ):
            return

        if request.method.lower() not in ['post', 'get', 'put']:
            return

        if re.match(self.request_wait_url_pattern, request.url):
            self.pending_requests += incr
            match incr:
                case 1:
                    self.requests.append(request.url)
                case -1:
                    self.requests.remove(request.url)

            logger.debug(
                'render: request_handler: %s %s (pending=%d) %s',
                request.url,
                '>>' if incr == 1 else '<<',
                self.pending_requests,
                self.requests
            )

    def load(self) -> Page:
        self.page.goto(self.url)
        if self.network_idle_check:
            self._wait_network_idle()
            self._attach_handlers(False)
        else:
            # simply wait network_idle_time if checks are not enabled
            self._sleep(self.network_idle_time)
            pass

        return self.page

    def _sleep(self, ms: int):
        self.page.wait_for_timeout(ms)
        pass

    def _wait_network_idle(self):
        quiet_time = 0
        while self.pending_requests > 0 or quiet_time < self.network_idle_time:
            logger.debug(
                'wait_network_idle: %d/%d: %s',
                quiet_time,
                self.network_idle_time,
                self.requests
            )
            self._sleep(1000)
            if self.pending_requests > 0:
                quiet_time = 0
            else:
                quiet_time += 1000
            pass
        logger.debug('wait_network_idle: %d/%d', quiet_time, self.network_idle_time)
        pass

    @staticmethod
    def _base_url(url):
        parsed_url = urlparse(url)
        return parsed_url.scheme + '://' + parsed_url.hostname

        pass
