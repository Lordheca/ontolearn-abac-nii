from typing import Any

from main._config import config
from main.commons.utils import HTTPMethod, make_http_request
from main.libs.log import get_logger


logger = get_logger(__name__)


async def get_access_decision(
    subject_attributes: dict[str, Any],
    resource_attributes: dict[str, Any],
    action: str,
    environment_attributes: dict[str, Any] | None = None,
) -> Any:
    """
    Call OPA to get an access decision.

    OPA input format:
        {
            "input": {
                "subject": {...},
                "resource": {...},
                "action": {...},
                "environments": {...}
            }
        }

    - `action` in this function is still a string (action name),
      but when sent to OPA it will be wrapped into a dict: {"name": action}
      to comply with the required format `{action: {}}`.
    """
    opa_input: dict[str, Any] = {
        "subject": subject_attributes or {},
        "resource": resource_attributes or {},
        # Wrap action string into object for OPA
        "action": {"name": action} if action is not None else {},
        "environments": environment_attributes or {},
    }

    opa_request_body = {"input": opa_input}
    logger.info(
        "Sending request to OPA",
        data={
            "opa_url": config.OPA_URL,
            "payload": opa_request_body,
        },
    )

    opa_response = await make_http_request(
        HTTPMethod.POST,
        config.OPA_URL,
        json_body=opa_request_body,
    )

    logger.info(
        "Received response from OPA",
        data={
            "opa_url": config.OPA_URL,
            "input": opa_input,
            "response": opa_response,
        },
    )

    # According to OPA standard, result is in the "result" field
    # Return raw response or just "result" depending on usage requirements.
    return opa_response.get("result", opa_response)
