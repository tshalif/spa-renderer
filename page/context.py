from typing import Dict, List, Tuple, Union

from playwright.sync_api import BrowserContext, Playwright

from util import config
from util.get_logger import get_logger

logger = get_logger(__name__)


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


def get_browser_context(
        playwright: Playwright,
        screen: str = None,
        debug: bool = None,
        user_agent: str = None,
        user_agent_append: str = None,
        device: str = None,
        extra_headers: Dict[str, str] = None
) -> Tuple[BrowserContext, str]:
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

        return context, resolved_device
    except Exception as e:
        browser.close()
        raise e
        pass
