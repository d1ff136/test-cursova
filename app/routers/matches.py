import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.match import Match, Round
from app.schemas.match import (
    MatchCreateParty,
    MatchCreateSolo,
    MatchFindParty,
    MatchFindSolo,
    MatchOut,
    RoundOut,
    RoundResultIn,
)
from app.services import match_service

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/solo", response_model=MatchOut, status_code=201)
def start_solo_match(payload: MatchCreateSolo, db: Session = Depends(get_db)):
    return match_service.create_solo_match(db, payload.player1_id, payload.player2_id)


@router.post("/party", response_model=MatchOut, status_code=201)
def start_party_match(payload: MatchCreateParty, db: Session = Depends(get_db)):
    return match_service.create_party_match(db, payload.team1_id, payload.team2_id)


@router.post("/solo/find", response_model=MatchOut, status_code=201)
def find_solo_match(payload: MatchFindSolo, db: Session = Depends(get_db)):
    """Автопідбір: сервер сам знаходить вільного суперника з найближчим Solo-MMR."""
    return match_service.find_and_create_solo_match(db, payload.player_id)


@router.post("/party/find", response_model=MatchOut, status_code=201)
def find_party_match(payload: MatchFindParty, db: Session = Depends(get_db)):
    """Автопідбір: сервер сам знаходить вільну команду з найближчим сумарним Party-MMR."""
    return match_service.find_and_create_party_match(db, payload.team_id)


@router.post("/{match_id}/cancel", response_model=MatchOut)
def cancel_match(match_id: uuid.UUID, db: Session = Depends(get_db)):
    """UPDATE: скасувати матч, поки в ньому не зіграно жодного раунду."""
    return match_service.cancel_match(db, match_id)


@router.delete("/{match_id}", status_code=204)
def delete_match(match_id: uuid.UUID, db: Session = Depends(get_db)):
    """DELETE: видалити матч (лише скасований або ще без зіграних раундів)."""
    match_service.delete_match(db, match_id)


@router.get("/{match_id}", response_model=MatchOut)
def get_match(match_id: uuid.UUID, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(404, "Матч не знайдено")
    return match


@router.post("/{match_id}/rounds", response_model=RoundOut, status_code=201)
def play_round(match_id: uuid.UUID, payload: RoundResultIn, db: Session = Depends(get_db)):
    """
    Додає результат одного раунду "Орел/Решка".
    Коли одна зі сторін набирає 2 перемоги - матч автоматично завершується
    і перераховується MMR обох сторін.
    """
    return match_service.submit_round(db, match_id, payload.coin_choice)


@router.get("/{match_id}/rounds", response_model=list[RoundOut])
def list_rounds(match_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(Round).filter(Round.match_id == match_id).order_by(Round.round_number).all()