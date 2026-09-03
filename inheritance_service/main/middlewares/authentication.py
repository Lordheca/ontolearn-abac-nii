import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from main import config
from main.commons.exceptions import ErrorCode, Forbidden
from main.schemas.access_decision import AuthorizationRequest


jwt_header = HTTPBearer(auto_error=False)


def validate_jwt(
    data: AuthorizationRequest,
    creds: HTTPAuthorizationCredentials = Depends(jwt_header),
) -> dict:
    """
    Validate JWT token and ensure the 'sub' claim matches the subject.id from request body.

    This function receives AuthorizationRequest data from the request body (parsed by FastAPI),
    then validates that the JWT token's 'sub' claim matches the subject.id.
    """
    credentials_exception = Forbidden(
        error_message="Invalid credentials",
        error_code=ErrorCode.FORBIDDEN,
    )

    if creds is None:
        raise credentials_exception

    token = creds.credentials
    try:
        payload = jwt.decode(
            jwt=token,
            key=config.SECRET_KEY,
            algorithms=config.ALGORITHM,
            options={
                "verify_signature": True,
                # "verify_exp": True,
                # "verify_nbf": True,
                # "verify_iat": True,
            },
        )

        # Validate that the 'sub' claim in JWT matches the subject.id from request body
        if not payload or payload.get("sub") != data.subject.id:
            raise credentials_exception
        return payload

    except jwt.DecodeError:
        raise credentials_exception
