from sqlalchemy import Column, Enum, Integer, SmallInteger, String, UniqueConstraint

from app.database import Base
from app.models.enums import GameMode


class Rank(Base):
    """Довідник рангів: Bronze/Silver/Gold мають рівні 1-3, Diamond - єдиний топ-ранг."""

    __tablename__ = "ranks"
    __table_args__ = (
        UniqueConstraint("mode", "name", "tier", name="uq_rank_mode_name_tier"),
        UniqueConstraint("mode", "sort_order", name="uq_rank_mode_sort_order"),
    )

    id = Column(Integer, primary_key=True)
    mode = Column(Enum(GameMode, name="game_mode"), nullable=False)
    name = Column(String(32), nullable=False)          # Bronze / Silver / Gold / Diamond
    tier = Column(SmallInteger, nullable=True)          # 1..3, NULL для Diamond
    min_mmr = Column(Integer, nullable=False)
    max_mmr = Column(Integer, nullable=True)            # NULL = без верхньої межі
    sort_order = Column(Integer, nullable=False)

    @property
    def display_name(self) -> str:
        return f"{self.name} {self.tier}" if self.tier else self.name
