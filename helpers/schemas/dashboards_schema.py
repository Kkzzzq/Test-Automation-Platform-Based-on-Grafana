from pydantic import BaseModel


class GetDashboardSchema(BaseModel):
    id: int
    timezone: str
    title: str = "Dashboard for API"
    uid: str


class GetDashboardsWithIncorrectCredentialsSchema(BaseModel):
    message: str = "invalid username or password"
    messageId: str | None = None
