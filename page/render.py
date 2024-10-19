from typing import Callable, List, Literal, Tuple, Union

from playwright.sync_api import Page, Playwright, TimeoutError, sync_playwright

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
        device: str = None
) -> Tuple[str, str]:
    chromium = playwright.chromium  # or "firefox" or "webkit".

    if debug is None:
        debug = config.get('debug')

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

        context = browser.new_context(**device_conf, ignore_https_errors=True)

        page = context.new_page()

        page.set_default_timeout(config.get('default_timeout'))

        page.goto(url)

        if config.get('warm_page_reload'):
            logger.debug('render: page warmup reload')
            page.reload()
            pass

        max_tries = config.get('max_tries')
        for i in range(max_tries):
            try:
                _wait_ready(page, ready_conditions)
            except TimeoutError as e:
                if i < max_tries - 1:
                    logger.debug(
                        'render: retrying (%d/%d)',
                        i + 1,
                        max_tries - 1
                    )
                    page.reload()
                    continue
                raise e
            pass

        page.evaluate(
            "document.querySelectorAll('script').forEach(s => s.remove())"
        )

        if remove_elements:
            for selector in remove_elements:
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


def render(
        url: str,
        ready_conditions: List[ReadyCondition] = None,
        remove_elements: List[str] = None,
        on_ready: OnPageReady = None,
        add_base_url=None,
        screen: str = None,
        user_agent=None,
        debug: bool = None,
        user_agent_append: str = None,
        device: str = None
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
            device=device
        )
        pass

    if config.get('store_pages'):
        store_page(html, url, resolved_device)
        pass

    return html
