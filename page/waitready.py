from typing import List, Literal, Tuple

from playwright.sync_api import Page

from util.get_logger import get_logger

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


def wait_ready(page, ready_conditions: List[ReadyCondition]) -> Page:
    while True:
        condition_matched, ready_conditions = _wait_conditions(
            page,
            ready_conditions or []
        )
        if not condition_matched:  # no more conditions to match
            break
        pass
    return page
