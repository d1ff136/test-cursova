from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.crud import rating as rating_crud
from app.database import get_db
from app.models.enums import GameMode
from app.schemas.rating import LeaderboardEntry

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/{mode}", response_model=list[LeaderboardEntry])
def get_leaderboard(
    mode: GameMode,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_dir: Literal["asc", "desc"] = Query("desc", description="Сортування за MMR: desc (спадання) або asc"),
    db: Session = Depends(get_db),
):
    """Глобальний рейтинг гравців режиму (Solo або Party) з пагінацією (limit/offset)
    та вибором напрямку сортування за MMR."""
    rows = rating_crud.get_leaderboard(db, mode, limit, offset, sort_dir)
    return [
        LeaderboardEntry(
            rank_position=offset + i + 1,
            username=user.username,
            mmr=player_rating.mmr,
            rank_name=rank.display_name if rank else "Unranked",
        )
        for i, (player_rating, user, rank) in enumerate(rows)
    ]