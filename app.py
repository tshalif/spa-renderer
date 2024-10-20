from typing import Annotated, List, Literal, Optional, Dict

import uvicorn
from fastapi import FastAPI, Header, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from page import ReadyCondition, render
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
    message: Optional[str] = Field(None, description="Exception Information")
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
        debug: bool = None
) -> Response:
    ready_conditions: List[ReadyCondition] = config.get('ready_conditions')

    remove_elements = config.get('remove_elements')
    data = render(
        url,
        ready_conditions=ready_conditions,
        remove_elements=remove_elements,
        add_base_url=add_base_url,
        screen=screen,
        user_agent=user_agent,
        user_agent_append=user_agent_append,
        device=device,
        debug=debug
    )
    return HTMLResponse(data)


@app.post('/render', response_model=RenderResponse)
def render_post(
        url: str,
        checks: List[ReadinessChecks],
        extra_headers: Dict[str, str] = None,
        screen: str = None,
        user_agent: str = None,
        user_agent_append: str = None,
        debug: bool = None,
        remove_elements: List[str] = None,
        add_base_url: bool = None,
        device: str = None
):
    ready_conditions = [(k.when, k.selectors, k.state) for k in checks]

    data = render(
        url,
        ready_conditions=ready_conditions,
        remove_elements=remove_elements,
        add_base_url=add_base_url,
        screen=screen,
        user_agent=user_agent,
        debug=debug,
        user_agent_append=user_agent_append,
        device=device,
        extra_headers=extra_headers
    )

    return RenderResponse(code=200, data=data).model_dump()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
