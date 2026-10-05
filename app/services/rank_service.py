"""Визначення рангу гравця (Bronze 1-3 / Silver 1-3 / Gold 1-3 / Diamond) за MMR."""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.enums import GameMode
from app.models.rank import Rank


def resolve_rank(db: Session, mode: GameMode, mmr: int) -> Optional[Rank]:
    """Повертає запис Rank, що відповідає поточному MMR гравця у заданому режимі."""
    return (
        db.query(Rank)
        .filter(
            Rank.mode == mode,
            Rank.min_mmr <= mmr,
            (Rank.max_mmr.is_(None)) | (Rank.max_mmr >= mmr),
        )
        .order_by(Rank.sort_order.desc())
        .first()
    )


def is_top_rank(rank: Optional[Rank]) -> bool:
    """Diamond - єдиний ранг без верхньої межі MMR."""
    return rank is not None and rank.max_mmr is None
