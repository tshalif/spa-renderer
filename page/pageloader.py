import re
from typing import List
from playwright.sync_api import Page, Request
from util import config
from urllib.parse import urlparse
from util.get_logger import get_logger

logger = get_logger(__name__)


class PageLoader:
    requests: List[str] = []

    def __init__(self, page: Page, url: str):
        self.page = page
        self.url = url
        self.pending_requests = 0
        base_url_pattern = re.escape(self._base_url(url))
        self.request_wait_url_pattern = (
                config.get('request_wait_url_pattern') or r'^@BASE_URL@(/|\?|#$)'
        ).replace('@BASE_URL@', base_url_pattern)

        self._attach_handlers(True)

        pass

    def _attach_handlers(self, attach: bool):
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

    def  _handle_request(self, request: Request):
        self._request_handler(request, 1)
        pass

    def  _handle_response(self, request: Request):
        self._request_handler(request, -1)
        pass

    def _request_handler(self, request: Request, incr: int):
        if re.match(r'.*\.(png|jpg|jpeg|gif|ico|svg|eot|ttf|woff2?|otf|css|js)$', request.url):
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
        self._wait_network_idle()
        self._attach_handlers(False)
        return self.page

    def _sleep(self, ms: int):
        self.page.wait_for_timeout(ms)
        pass

    def _wait_network_idle(self):
        network_idle_time = config.get('network_idle_time')
        quiet_time = 0
        while self.pending_requests > 0 or quiet_time < network_idle_time:
            logger.debug(
                'wait_network_idle: %d/%d: %s',
                quiet_time,
                network_idle_time,
                self.requests
            )
            self._sleep(1000)
            if self.pending_requests > 0:
                quiet_time = 0
            else:
                quiet_time += 1000
            pass
        logger.debug('wait_network_idle: %d/%d', quiet_time, network_idle_time)
        pass

    @staticmethod
    def _base_url(url):
        parsed_url = urlparse(url)
        return parsed_url.scheme + '://' + parsed_url.hostname

        pass
