from pydantic import BaseModel


class CreateUserSchema(BaseModel):
    id: int
    message: str = "User created"


class ChangeUserPassword(BaseModel):
    message: str = "User password updated"


class DeleteUserSchema(BaseModel):
    message: str = "User deleted"


class CreateExistingUserSchema(BaseModel):
    message: str
    status: str | None = None


class CreateBadRequestSchema(BaseModel):
    message: str


class GetDashboardWithLowAccessSchema(BaseModel):
    message: str


class Get404DashboardSchema(BaseModel):
    message: str
