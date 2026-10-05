import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.enums import CoinSide, GameMode, MatchStatus


class MatchCreateSolo(BaseModel):
    mode: GameMode = GameMode.solo
    player1_id: uuid.UUID
    player2_id: uuid.UUID


class MatchCreateParty(BaseModel):
    mode: GameMode = GameMode.party
    team1_id: uuid.UUID
    team2_id: uuid.UUID


class MatchFindSolo(BaseModel):
    """Швидкий пошук суперника за MMR для Solo-режиму."""

    player_id: uuid.UUID


class MatchFindParty(BaseModel):
    """Швидкий пошук команди-суперника за сумарним MMR для Party-режиму."""

    team_id: uuid.UUID


class RoundResultIn(BaseModel):
    """Вибір гравця для одного раунду 'Орел/Решка'.

    Фактичний результат підкидання (coin_result) визначає СЕРВЕР випадковим чином
    — клієнт не передає і не може вплинути на результат, щоб унеможливити
    підбір/фіксацію переможця матчу.
    """

    coin_choice: CoinSide       # що обрав гравець з нижчим MMR (Орел/Решка)


class RoundOut(BaseModel):
    round_number: int
    coin_choice: CoinSide
    coin_result: CoinSide
    winner_side: int
    created_at: datetime

    class Config:
        from_attributes = True


class MatchOut(BaseModel):
    id: uuid.UUID
    mode: GameMode
    status: MatchStatus
    best_of: int
    side1_mmr_snapshot: Optional[int]
    side2_mmr_snapshot: Optional[int]
    coin_chooser_user_id: Optional[uuid.UUID]
    winner_side: Optional[int]
    created_at: datetime
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True