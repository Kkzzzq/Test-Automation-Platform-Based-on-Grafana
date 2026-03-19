from pydantic import BaseModel


class OrganizationAddressSchema(BaseModel):
    address1: str = ""
    address2: str = ""
    city: str = ""
    zipCode: str = ""
    state: str = ""
    country: str = ""


class CreateOrganizationSchema(BaseModel):
    orgId: int | str
    message: str = "Organization created"


class AddUserInOrganizations(BaseModel):
    message: str = "User added to organization"
    userId: int


class GetOrganizationsById(BaseModel):
    id: int
    name: str
    address: OrganizationAddressSchema


class UpdateUserInOrg(BaseModel):
    message: str = "Organization user updated"
