from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Subject(BaseModel):
    id: int | str
    model_config = ConfigDict(extra="allow")


class Resource(BaseModel):
    id: int | str
    model_config = ConfigDict(extra="allow")


class Action(BaseModel):
    name: str
    metadata: dict[str, Any] | None = None


class AuthorizationRequest(BaseModel):
    subject: Subject
    resource: Resource
    environment: dict[str, dict[str, Any]] | None = Field(
        default=None,
        alias="environments",
    )
    action: Action

    model_config = ConfigDict(populate_by_name=True)


class AuthorizationResponse(BaseModel):
    result: bool
    environment_attributes: dict[str, Any] | None = None
    subject: Subject  #
    action: Action
    resource: Resource
