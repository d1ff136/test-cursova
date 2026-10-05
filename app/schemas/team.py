import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    name: Optional[str] = None
    member_user_ids: List[uuid.UUID] = Field(min_length=3, max_length=3)
    is_permanent: bool = False


class TeamUpdate(BaseModel):

    name: Optional[str] = None
    is_permanent: Optional[bool] = None


class TeamOut(BaseModel):
    id: uuid.UUID
    name: Optional[str]
    is_permanent: bool
    member_user_ids: List[uuid.UUID]

    class Config:
        from_attributes = True