from pydantic import BaseModel


class CreateOrganizationResponse(BaseModel):
    orgId: int
    message: str


class AddUserInOrganizations(BaseModel):
    message: str
    userId: int


class GetOrganizationsById(BaseModel):
    id: int
    name: str


class UpdateUserInOrg(BaseModel):
    message: str
