from typing import Annotated, Dict, List, Literal, Optional

import uvicorn
from fastapi import FastAPI, Header, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from page import render
from util import config

app = FastAPI()


class ReadinessChecks(BaseModel):
    when: str = Field(
        'body',
        description='Apply these checks only when this locator is visible'
    )
    selectors: List[str] = Field(
        None,
        description='css/xpath selectors to check'
    )
    state: Literal["attached", "detached", "hidden", "visible"] = Field(
        "attached",
        description='Expected selector state'
    )


class RenderResponse(BaseModel):
    code: int = Field(200, description="Status Code")
    s3_url: Optional[str] = Field(None, description="S3 cache URL")
    message: Optional[str] = Field(None, description="Exception Information")
    cache_hit: Optional[bool] = Field(None, description="Cache hit")
    cache_url: Optional[str] = Field(None, description="Cache URL")
    data: Optional[str] = Field(
        None,
        description="Rendered SPA page (DOM dump)"
    )


@app.get('/render')
def render_get(
        url: str,
        add_base_url: bool = None,
        device: str = None,
        screen: str = None,
        user_agent: Annotated[str | None, Header()] = None,
        user_agent_append: str = None,
        debug: bool = None,
        network_idle_check: bool = None,
        s3_store_pages: bool = None,
        x_spa_renderer_return_cached: Annotated[bool | None, Header()] = None,
) -> Response:

    if network_idle_check is not None:
        config.set('network_idle_check', network_idle_check)
    if debug is not None:
        config.set('debug', debug)
    if add_base_url is not None:
        config.set('add_base_url', add_base_url)
    if user_agent_append is not None:
        config.set('user_agent_append', user_agent_append)
    if s3_store_pages is not None:
        config.set('s3_store_pages', s3_store_pages)
    if x_spa_renderer_return_cached is not None:
        config.set('s3_return_cached_pages', x_spa_renderer_return_cached)
        pass

    data, cache_hit, _ = render(
        url,
        screen=screen,
        user_agent=user_agent,
        device=device
    )

    return HTMLResponse(
        content=data,
        headers={
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'X-Spa-Renderer-Cache-Hit': str(cache_hit)
        }
    )


@app.post('/render', response_model=RenderResponse)
def render_post(
        url: str,
        checks: List[ReadinessChecks] = None,
        extra_headers: Dict[str, str] = None,
        screen: str = None,
        user_agent: str = None,
        user_agent_append: str = None,
        debug: bool = None,
        remove_elements: List[str] = None,
        add_base_url: bool = None,
        device: str = None,
        network_idle_check: bool = None,
        s3_store_pages: bool = None,
        use_cached_pages: bool = None
):
    if checks is not None:
        ready_conditions = [(k.when, k.selectors, k.state) for k in checks]
        config.set('ready_conditions', ready_conditions)
    if network_idle_check is not None:
        config.set('network_idle_check', network_idle_check)
    if debug is not None:
        config.set('debug', debug)
    if add_base_url is not None:
        config.set('add_base_url', add_base_url)
    if user_agent_append is not None:
        config.set('user_agent_append', user_agent_append)
    if remove_elements is not None:
        config.set('remove_elements', remove_elements)
    if extra_headers is not None:
        config.set('extra_http_headers', extra_headers)
    if s3_store_pages is not None:
        config.set('s3_store_pages', s3_store_pages)
    if use_cached_pages is not None:
        config.set('s3_return_cached_pages', use_cached_pages)
    else:
        config.set('s3_return_cached_pages', False)
        pass

    data, cache_hit, s3_url = render(
        url,
        screen=screen,
        user_agent=user_agent,
        device=device,
    )

    return RenderResponse(
        code=200,
        data=data,
        s3_url=s3_url,
        cache_hit=cache_hit,
        cache_url=s3_url
    ).model_dump()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
