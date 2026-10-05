import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import CoinSide, GameMode, MatchStatus


class Match(Base):
    """Матч. У Solo - 1 проти 1, у Party - команда 3х3 (перемога до 2 виграних раундів)."""

    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mode = Column(Enum(GameMode, name="game_mode"), nullable=False)
    status = Column(Enum(MatchStatus, name="match_status"), nullable=False, default=MatchStatus.pending)
    best_of = Column(SmallInteger, nullable=False, default=3)
    side1_mmr_snapshot = Column(Integer, nullable=True)
    side2_mmr_snapshot = Column(Integer, nullable=True)
    coin_chooser_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    winner_side = Column(SmallInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (CheckConstraint("winner_side IN (1, 2)", name="ck_match_winner_side"),)

    sides = relationship("MatchSide", back_populates="match", cascade="all, delete-orphan")
    rounds = relationship("Round", back_populates="match", cascade="all, delete-orphan")


class MatchSide(Base):
    """Одна зі сторін матчу: гравець (Solo) або команда (Party)."""

    __tablename__ = "match_sides"
    __table_args__ = (
        UniqueConstraint("match_id", "side", name="uq_match_side"),
        CheckConstraint(
            "(user_id IS NOT NULL AND team_id IS NULL) OR (user_id IS NULL AND team_id IS NOT NULL)",
            name="ck_match_side_user_xor_team",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    side = Column(SmallInteger, nullable=False)  # 1 або 2
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)

    match = relationship("Match", back_populates="sides")
    user = relationship("User")
    team = relationship("Team")


class Round(Base):
    """Окремий раунд гри "Орел/Решка" в межах матчу."""

    __tablename__ = "rounds"
    __table_args__ = (UniqueConstraint("match_id", "round_number", name="uq_round_number"),)

    id = Column(BigInteger, primary_key=True)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    round_number = Column(SmallInteger, nullable=False)
    coin_choice = Column(Enum(CoinSide, name="coin_side"), nullable=False)
    coin_result = Column(Enum(CoinSide, name="coin_side"), nullable=False)
    winner_side = Column(SmallInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    match = relationship("Match", back_populates="rounds")
