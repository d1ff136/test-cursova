import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.match import MatchSide
from app.models.team import Team, TeamMember
from app.schemas.team import TeamUpdate


def get_team(db: Session, team_id: uuid.UUID) -> Team | None:
    return db.query(Team).filter(Team.id == team_id).first()


def get_team_member_ids(db: Session, team_id: uuid.UUID) -> list[uuid.UUID]:
    return [m.user_id for m in db.query(TeamMember).filter(TeamMember.team_id == team_id).all()]


def update_team(db: Session, team: Team, payload: TeamUpdate) -> Team:
    """UPDATE: назва та/або статус "постійне паті"."""
    if payload.name is not None:
        team.name = payload.name
    if payload.is_permanent is not None:
        team.is_permanent = payload.is_permanent

    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def team_has_matches(db: Session, team_id: uuid.UUID) -> bool:
    return db.query(MatchSide).filter(MatchSide.team_id == team_id).first() is not None


def delete_team(db: Session, team: Team) -> None:
    """DELETE: фізичне видалення команди (та її team_members - ON DELETE CASCADE).

    Явна транзакція з rollback: якщо команда все ж прив'язана до матчу
    (match_sides.team_id не має ON DELETE CASCADE - БД поверне IntegrityError),
    відкочуємо зміни і повідомляємо про конфлікт, а не лишаємо сесію в
    невизначеному стані.
    """
    try:
        db.delete(team)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Команду не можна видалити - вона вже бере участь у матчі(ах)")