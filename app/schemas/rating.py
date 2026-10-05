import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.enums import GameMode


class RankOut(BaseModel):
    id: int
    mode: GameMode
    name: str
    tier: Optional[int]
    min_mmr: int
    max_mmr: Optional[int]

    class Config:
        from_attributes = True


class PlayerRatingOut(BaseModel):
    user_id: uuid.UUID
    mode: GameMode
    mmr: int
    wins: int
    losses: int
    matches_played: int
    rank: Optional[RankOut] = None
    world_rank: Optional[int] = None  # заповнюється лише для Diamond

    class Config:
        from_attributes = True


class RatingHistoryOut(BaseModel):
    mode: GameMode
    match_id: Optional[uuid.UUID]
    mmr_before: int
    mmr_after: int
    delta: int
    created_at: datetime

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    rank_position: int
    username: str
    mmr: int
    rank_name: str
