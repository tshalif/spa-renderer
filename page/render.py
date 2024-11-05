from datetime import datetime, timezone
from typing import Callable, Dict, List, Tuple

from playwright.sync_api import Page, TimeoutError, sync_playwright

from util import config
from util.get_logger import get_logger

from .cache import get_page, store_page
from .context import get_browser_context
from .pageloader import PageLoader
from .waitready import ReadyCondition, wait_ready

type OnPageReady = Callable[[Page], None]


logger = get_logger(__name__)


def render_page(context, ready_conditions, url):
    if config.get('preload_pages'):
        page = context.new_page()
        page.goto(url)
        page.close()
        pass
    max_tries = config.get('max_tries')
    for i in range(max_tries):
        try:
            page_loader = PageLoader(context.new_page(), url)
            page = page_loader.load()
            return wait_ready(page, ready_conditions)
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
    raise AssertionError('HDIGH: could not resolve page')


def delete_elements(page: Page, sel: str):
    page.evaluate(
        f"document.querySelectorAll('{sel}').forEach(s => s.remove())"
    )
    pass


def clean_page(page, remove_elements):

    delete_elements(  # remove javascript `script` tags
        page,
        'script:not([type]),script[type="text/javascript"],script[type="module"]'  # noqa: E501
    )

    if remove_elements:
        for selector in remove_elements:
            logger.debug('render: removing elements: %s', selector)
            delete_elements(page, selector)
            pass
        pass
    return page


def add_meta(page: Page, name: str, content: str):
    page.evaluate(f"""
    let meta = document.createElement('meta');
    meta.name = '{name}';
    meta.content = '{content}';
    document.head.insertBefore(meta, document.head.firstElementChild);
    """)
    pass


def add_base(add_base_url, page, url):
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


def render(
        url: str,
        on_ready: OnPageReady = None,
        screen: str = None,
        user_agent=None,
        device: str = None
) -> Tuple[str, str]:
    config.log_conf()

    ready_conditions: List[ReadyCondition] = config.get('ready_conditions')
    remove_elements: List[str] = config.get('remove_elements')
    add_base_url: bool = config.get('add_base_url')
    debug: bool = config.get('debug')
    user_agent_append: str = config.get('user_agent_append')
    extra_headers: Dict[str, str] = config.get('extra_http_headers')

    if debug is None:
        debug = config.get('debug')
        pass

    if extra_headers is None:
        extra_headers = config.get('extra_http_headers') or {}
        pass

    with sync_playwright() as playwright:

        context, resolved_device = get_browser_context(
            playwright,
            screen=screen,
            debug=debug,
            user_agent=user_agent,
            user_agent_append=user_agent_append,
            device=device,
            extra_headers=extra_headers
        )

        err = None
        try:
            if config.get(
                    's3_store_pages'
            ) and config.get(
                's3_return_cached_pages'
            ):
                html, s3_url = get_page(resolved_device, url)
                if html:
                    return html, s3_url
                pass

            page = render_page(
                context,
                ready_conditions,
                url
            )

            clean_page(page, remove_elements)

            add_meta(
                page,
                'x-spa-renderer-timestamp',
                datetime.now(timezone.utc).isoformat()
            )
            add_meta(page, 'x-spa-renderer-device', resolved_device)
            add_base(add_base_url, page, url)

            s3_url = ''
            html = page.content()
            if config.get('s3_store_pages'):
                s3_url = store_page(html, url, resolved_device)
                pass
            return html, s3_url

        except Exception as e:
            err = e
            logger.exception('render: error while rendering %s: %s', url, e)
            raise e
        finally:
            if on_ready and not err:
                on_ready(page)
                pass
            pass
