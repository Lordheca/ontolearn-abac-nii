from collections.abc import Mapping
from typing import Any

import httpx

from main.enums import HTTPMethod


async def make_http_request(
    method: HTTPMethod,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    data: Mapping[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    Generic async HTTP request helper.

    - Supports common HTTP methods (GET, POST, PUT, PATCH, DELETE, ...)
    - Supports query params (`params`), JSON body (`json_body`), and form data (`data`)
    - Returns the decoded JSON response as a dict
    """

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method=method.value,
            url=url,
            params=params,
            json=json_body,
            data=data,
            headers=headers,
        )
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()
