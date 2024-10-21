from typing import Callable, Dict, List, Union

from playwright.sync_api import Page, TimeoutError, sync_playwright

from util import config
from util.get_logger import get_logger

from .cache import store_page
from .context import get_browser_context
from .pageloader import PageLoader
from .waitready import ReadyCondition, wait_ready

type OnPageReady = Callable[[Page], None]


logger = get_logger(__name__)


def render_page(add_base_url, context, ready_conditions, remove_elements, url):
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
            wait_ready(page, ready_conditions)
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
    return page


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
        device: str = None,
        extra_headers: Dict[str, str] = None
) -> str:

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

        page = render_page(
            add_base_url,
            context,
            ready_conditions,
            remove_elements,
            url
        )

        if on_ready:
            on_ready(page)
            pass

        html = page.content()
        pass

    if config.get('store_pages'):
        store_page(html, url, resolved_device)
        pass

    return html
