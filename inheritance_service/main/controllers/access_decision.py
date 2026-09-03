from fastapi import APIRouter, Depends, HTTPException

from main._config import config
from main.commons.utils import HTTPMethod, make_http_request
from main.libs.access_lib import access_decision_lib, environment_attribute_lib
from main.middlewares.authentication import validate_jwt
from main.schemas.access_decision import AuthorizationRequest, AuthorizationResponse


router: APIRouter = APIRouter()


@router.post("/request_access", response_model=AuthorizationResponse)
async def request_access(
    data: AuthorizationRequest,
    _=Depends(validate_jwt),
):
    environment_attributes = None
    if data.environment:
        environment_attributes = (
            await environment_attribute_lib.get_environment_attributes(
                input_data=data.environment,
            )
        )

    # Call OPA with subject, resource, action, and environment attributes
    access_decision = await access_decision_lib.get_access_decision(
        subject_attributes=data.subject.model_dump(),
        resource_attributes=data.resource.model_dump(),
        action=data.action.name,
        environment_attributes=environment_attributes if data.environment else None,
    )
    return AuthorizationResponse(
        result=access_decision,
        environment_attributes=environment_attributes,
        subject=data.subject,
        action=data.action,
        resource=data.resource,
    )


@router.post("/request_access_decision")
async def request_direct_policy_engine_access_decision(data: dict):
    """
    Receive an input payload, forward it to OPA, and return OPA's decision.

    `data` is forwarded as-is as the JSON body to OPA. The response is expected
    to follow OPA's standard format: `{"result": ...}`.
    """
    try:
        opa_response = await make_http_request(
            HTTPMethod.POST,
            config.OPA_URL,
            json_body=data,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "OPA request error", "details": str(exc)},
        ) from exc

    return opa_response
