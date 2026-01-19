from pydantic import BaseModel


class ProfileContent(BaseModel):
    content: str
