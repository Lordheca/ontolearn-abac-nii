from pydantic import BaseModel


class SubjectRequestSchema(BaseModel):
    subject_id: int
    subject_type: str


class ResourceRequestSchema(BaseModel):
    resource_id: int | None = None
    resource_type: str
    resource_attributes_query: dict | None = None


class InheritanceRetrieveParams(BaseModel):
    subject_metadata: SubjectRequestSchema
    resource_metadata: ResourceRequestSchema
    action: str


class InheritanceRetrieveResponse(BaseModel):
    subject_attributes: dict | None
    resource_attributes: list[dict] | None
    actions: list[str]
