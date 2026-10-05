import uuid

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import GameMode


class PlayerRating(Base):
    """Поточний MMR гравця в конкретному режимі (Solo або Party)."""

    __tablename__ = "player_ratings"
    __table_args__ = (UniqueConstraint("user_id", "mode", name="uq_player_rating_user_mode"),)

    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode = Column(Enum(GameMode, name="game_mode"), nullable=False)
    mmr = Column(Integer, nullable=False, default=1000)
    rank_id = Column(Integer, ForeignKey("ranks.id"), nullable=True)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    matches_played = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="ratings")
    rank = relationship("Rank")


class RatingHistory(Base):
    """Аудит зміни рейтингу гравця після кожного матчу."""

    __tablename__ = "rating_history"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode = Column(Enum(GameMode, name="game_mode"), nullable=False)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)
    mmr_before = Column(Integer, nullable=False)
    mmr_after = Column(Integer, nullable=False)
    delta = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
