from fastapi import APIRouter, Depends

from main._db import get_db_session
from main.commons.resources import Resource
from main.libs.retrieve_lib import environment_retrieve_lib, inheritance_retrieve_lib
from main.schemas.inheritance_retrieve import (
    InheritanceRetrieveParams,
    InheritanceRetrieveResponse,
)
from main.services import resource_service


router: APIRouter = APIRouter()


@router.post("/retrieve_access_information", response_model=InheritanceRetrieveResponse)
async def retrieve_access_information(
    data: InheritanceRetrieveParams,
    session=Depends(get_db_session),
):
    # Retrieve subject attributes
    subject_attributes: dict = await inheritance_retrieve_lib.get_subject_attributes(
        session=session,
        subject_id=data.subject_metadata.subject_id,
        subject_type=data.subject_metadata.subject_type,
    )

    # Retrieve resource attributes (as Resource instances)
    resource_instances: list[Resource] = await resource_service.get_resource_attributes(
        session=session,
        resource_id=data.resource_metadata.resource_id,
        resource_type=data.resource_metadata.resource_type,
        resource_attributes_query=data.resource_metadata.resource_attributes_query,
    )

    # Retrieve actions from inheritance tree
    actions = inheritance_retrieve_lib.get_actions(action=data.action)

    # Retrieve additional environment attributes for resources
    resource_attributes_list = await environment_retrieve_lib.get_additional_environment_attributes_for_resources(
        resource_instances=resource_instances,
    )

    return InheritanceRetrieveResponse(
        subject_attributes=subject_attributes,
        resource_attributes=resource_attributes_list,
        actions=actions,
    )
