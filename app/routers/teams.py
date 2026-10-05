import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import team as team_crud
from app.database import get_db
from app.models.team import Team, TeamMember
from app.schemas.team import TeamCreate, TeamOut, TeamUpdate

router = APIRouter(prefix="/teams", tags=["teams"])


def _to_out(team: Team, member_ids: list[uuid.UUID]) -> TeamOut:
    return TeamOut(
        id=team.id,
        name=team.name,
        is_permanent=team.is_permanent,
        member_user_ids=member_ids,
    )


@router.post("/", response_model=TeamOut, status_code=201)
def create_team(payload: TeamCreate, db: Session = Depends(get_db)):
    if len(set(payload.member_user_ids)) != 3:
        raise HTTPException(400, "Команда Party-режиму повинна містити рівно 3 різних гравців")

    # Явна транзакція: якщо будь-який з member_user_ids не існує в users (FK-порушення)
    # або гравець уже входить у цю ж команду (UNIQUE), відкочуємо УСІ зміни - команда
    # не повинна лишитись напів-створеною (без частини учасників).
    team = Team(name=payload.name, is_permanent=payload.is_permanent)
    db.add(team)
    try:
        db.flush()
        for uid in payload.member_user_ids:
            db.add(TeamMember(team_id=team.id, user_id=uid))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Не вдалося створити команду: перевірте ID гравців (можливо, такого користувача не існує)")

    db.refresh(team)
    return _to_out(team, payload.member_user_ids)


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: uuid.UUID, db: Session = Depends(get_db)):
    team = team_crud.get_team(db, team_id)
    if not team:
        raise HTTPException(404, "Команду не знайдено")
    return _to_out(team, team_crud.get_team_member_ids(db, team_id))


@router.patch("/{team_id}", response_model=TeamOut)
def update_team(team_id: uuid.UUID, payload: TeamUpdate, db: Session = Depends(get_db)):
    """UPDATE: назва та/або is_permanent (склад команди - незмінний після створення)."""
    team = team_crud.get_team(db, team_id)
    if not team:
        raise HTTPException(404, "Команду не знайдено")
    updated = team_crud.update_team(db, team, payload)
    return _to_out(updated, team_crud.get_team_member_ids(db, team_id))


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: uuid.UUID, db: Session = Depends(get_db)):
    """DELETE: фізичне видалення команди - лише якщо вона ще не брала участі в матчах."""
    team = team_crud.get_team(db, team_id)
    if not team:
        raise HTTPException(404, "Команду не знайдено")
    if team_crud.team_has_matches(db, team_id):
        raise HTTPException(409, "Команду не можна видалити - вона вже брала участь у матчі(ах)")
    try:
        team_crud.delete_team(db, team)
    except ValueError as e:
        raise HTTPException(409, str(e))