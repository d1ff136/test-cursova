import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import GameMode
from app.models.rank import Rank
from app.models.rating import PlayerRating
from app.models.user import User
from app.services.rank_service import is_top_rank


def get_player_rating(db: Session, user_id: uuid.UUID, mode: GameMode) -> Optional[PlayerRating]:
    return (
        db.query(PlayerRating)
        .filter(PlayerRating.user_id == user_id, PlayerRating.mode == mode)
        .first()
    )


def get_world_rank_position(db: Session, user_id: uuid.UUID, mode: GameMode) -> Optional[int]:
    """
    Позиція гравця у світовому рейтингу для його режиму.
    За ТЗ показується додатково лише гравцям рангу Diamond,
    але функція повертає позицію для будь-кого - фільтрація по Diamond
    відбувається на рівні виклику (router).
    """
    subq = (
        db.query(
            PlayerRating.user_id,
            func.rank().over(order_by=PlayerRating.mmr.desc()).label("position"),
        )
        .filter(PlayerRating.mode == mode)
        .subquery()
    )
    row = db.query(subq.c.position).filter(subq.c.user_id == user_id).first()
    return row.position if row else None


def get_leaderboard(db: Session, mode: GameMode, limit: int = 100, offset: int = 0, sort_dir: str = "desc"):
    """Топ гравців режиму, з пагінацією (limit/offset) і сортуванням за MMR."""
    order = PlayerRating.mmr.asc() if sort_dir == "asc" else PlayerRating.mmr.desc()
    return (
        db.query(PlayerRating, User, Rank)
        .join(User, User.id == PlayerRating.user_id)
        .outerjoin(Rank, Rank.id == PlayerRating.rank_id)
        .filter(PlayerRating.mode == mode)
        .order_by(order)
        .offset(offset)
        .limit(limit)
        .all()
    )