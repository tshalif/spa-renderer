import re
from time import sleep
from typing import Callable, List, Literal, Tuple, Union, Dict
from urllib.parse import urlparse

from playwright.sync_api import Page, Playwright, TimeoutError, sync_playwright, Request, Response, BrowserContext
from pylint.checkers.utils import returns_bool

from util import config
from util.get_logger import get_logger

from .cache import store_page

type OnPageReady = Callable[[Page], None]
type ReadyCondition = Tuple[
    str,
    List[str],
    Literal["attached", "detached", "hidden", "visible"]
]


logger = get_logger(__name__)


class PageLoader:
    requests: List[str] = []

    def __init__(self, page: Page, url: str):
        self.page = page
        self.url = url
        self.pending_requests = 0
        base_url_pattern = re.escape(_base_url(url))
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

        # logger.debug(
        #     'render: _request_handler: %d: %s',
        #     incr,
        #     request.url
        # )

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

def _wait_conditions(page: Page, ready_conditions: List[ReadyCondition]):
    remaining_conditions: List[Tuple[str, List[str]]] = []
    condition_matched = False
    for selector, conditions, state in ready_conditions:
        if page.query_selector(selector):
            logger.debug('wait_conditions: selector=%s: matched', selector)
            for condition in conditions:
                logger.debug(
                    'wait_conditions: selector=%s: waiting for %s, state=%s',
                    selector,
                    condition,
                    state
                )
                page.wait_for_selector(condition, state=state)
                pass
            logger.debug('wait_conditions: selector=%s: satisfied', selector)
            condition_matched = True
            continue
        remaining_conditions.append((selector, conditions))
        pass
    return condition_matched, remaining_conditions


def _get_preset(user_agent: str):
    if user_agent:
        mapping: List[str, str] = config.get('user_agent_screen_mapping')
        for ua, preset in mapping:
            if ua in user_agent.lower():
                return preset
            pass
        pass

    return 'desktop'


def _resolve_device(
        devices: dict,
        device: str = None,
        user_agent: str = None
) -> Union[str, None]:
    device = device or config.get('device')

    if device:
        logger.debug('resolve_device: using declared device=%s', device)
        return device

    if user_agent:
        device_names = [k for k in devices.keys()]
        device_names.sort()
        device_names.reverse()
        for k in device_names:
            if user_agent in devices[k].get('user_agent', ''):
                logger.debug(
                    'resolve_device: user_agent match (full) device=%s',
                    k
                )
                return k
            pass
        for k in device_names:
            if k in user_agent:
                logger.debug(
                    'resolve_device: user_agent match (partial) device=%s',
                    k
                )
                return k
            pass
        pass
    return None


def _resolve_device_conf(
        devices: dict,
        device: str = None,
        screen: str = None,
        user_agent: str = None,
        user_agent_append: str = None
) -> Tuple[str, dict]:
    if not user_agent:
        user_agent = config.get('user_agent') or None
        pass

    if not user_agent_append:
        user_agent_append = config.get('user_agent_append') or None
        pass

    device = _resolve_device(devices, device, user_agent)

    if device:
        conf = devices[device]
    else:
        device = _get_preset(user_agent)
        screen = screen or config.get('screen_presets').get(device)
        conf = dict(
            user_agent=config.get('default_user_agent')
        )
        pass

    if screen:
        width, height = screen.split('x')
        conf.update(viewport=dict(width=int(width), height=int(height)))
        pass

    if user_agent:
        conf.update(user_agent=user_agent)
        pass

    if conf['user_agent'] and user_agent_append:
        conf['user_agent'] = '%s %s' % (conf['user_agent'], user_agent_append)
        pass

    return device, conf


def _base_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + '://' + parsed_url.hostname


def _render_internal(
        playwright: Playwright,
        url: str,
        ready_conditions: List[ReadyCondition] = None,
        remove_elements: List[str] = None,
        on_ready: OnPageReady = None,
        add_base_url=None,
        screen: str = None,
        debug: bool = None,
        user_agent: str = None,
        user_agent_append: str = None,
        device: str = None,
        extra_headers: Dict[str, str] = None
) -> Tuple[str, str]:
    chromium = playwright.chromium  # or "firefox" or "webkit".

    if debug is None:
        debug = config.get('debug')
        pass

    if extra_headers is None:
        extra_headers = config.get('extra_http_headers') or {}
        pass

    browser = chromium.launch(headless=(not debug))

    try:
        resolved_device, device_conf = _resolve_device_conf(
            playwright.devices,
            device=device,
            screen=screen,
            user_agent=user_agent,
            user_agent_append=user_agent_append
        )

        logger.debug(
            'render: using device=%s, device_conf=%s',
            resolved_device,
            device_conf
        )

        context = browser.new_context(
            **device_conf,
            ignore_https_errors=True,
            extra_http_headers=extra_headers,
        )

        if config.get('preload_pages'):
            page = context.new_page()
            page.goto(url)
            page.close()
            pass

        page: Union[Page, None] = None

        max_tries = config.get('max_tries')
        for i in range(max_tries):
            try:
                page_loader = PageLoader(context.new_page(), url)
                page = page_loader.load()
                _wait_ready(page, ready_conditions)
                break
            except TimeoutError as e:
                if i < max_tries - 1:
                    logger.debug(
                        'render: retrying (%d/%d)',
                        i + 1,
                        max_tries - 1
                    )
                    continue
                raise e
            pass

        assert page is not None

        page.evaluate(
            "document.querySelectorAll('script').forEach(s => s.remove())"
        )

        if remove_elements:
            for selector in remove_elements:
                logger.debug('render: removing elements: %s', selector)
                page.evaluate(
                    f"document.querySelectorAll('{selector}').forEach(s => s.remove())"  # noqa: E501
                )
                pass
            pass

        if add_base_url is None:
            add_base_url = config.get('add_base_url')
            pass

        if add_base_url:
            page.evaluate(f"""
                let base = document.createElement('base');
                base.href = '{url}';
                document.head.insertBefore(base, document.head.firstElementChild);
                """)  # noqa: E501
            pass

        if on_ready:
            on_ready(page)
            pass
        return page.content(), resolved_device
    finally:
        browser.close()
        pass


def _wait_ready(page, ready_conditions):
    while True:
        condition_matched, ready_conditions = _wait_conditions(
            page,
            ready_conditions or []
        )
        if not condition_matched:
            break
        pass


def render(url: str,
           ready_conditions: List[ReadyCondition] = None,
           remove_elements: List[str] = None,
           on_ready: OnPageReady = None,
           add_base_url=None,
           screen: str = None,
           user_agent=None,
           debug: bool = None,
           user_agent_append: str = None,
           device: str = None,
           extra_headers: Dict[str, str] = None
   ) -> str:
    with sync_playwright() as playwright:
        html, resolved_device = _render_internal(
            playwright,
            url,
            ready_conditions=ready_conditions,
            remove_elements=remove_elements,
            on_ready=on_ready,
            add_base_url=add_base_url,
            screen=screen,
            user_agent=user_agent,
            debug=debug,
            user_agent_append=user_agent_append,
            device=device,
            extra_headers=extra_headers
        )
        pass

    if config.get('store_pages'):
        store_page(html, url, resolved_device)
        pass

    return html
