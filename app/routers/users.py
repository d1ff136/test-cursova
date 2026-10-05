import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import user as user_crud
from app.crud import rating as rating_crud
from app.database import get_db
from app.models.enums import GameMode, UserRole
from app.schemas.rating import PlayerRatingOut
from app.schemas.user import UserCreate, UserLogin, UserOut, UserUpdate
from app.services.rank_service import is_top_rank

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(db: Session, requester_id: uuid.UUID) -> None:
    """Спрощена авторизація без токенів/сесій (узгоджено зі стилем усього API:
    ролі перевіряються через requester_id, як матчі/команди ідентифікуються через
    прямі UUID). У продакшн-варіанті requester_id замінюється на дані з JWT."""
    requester = user_crud.get_user(db, requester_id)
    if not user_crud.is_admin(requester):
        raise HTTPException(403, "Ця дія доступна лише активному користувачу з роллю 'admin'")


@router.post("/", response_model=UserOut, status_code=201)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    if user_crud.get_user_by_username(db, payload.username):
        raise HTTPException(409, "Ім'я користувача вже зайняте")
    return user_crud.create_user(db, payload)


@router.post("/login", response_model=UserOut)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = user_crud.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(401, "Невірне ім'я користувача або пароль")
    if not user.is_active:
        raise HTTPException(403, "Акаунт деактивовано")
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "Користувача не знайдено")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: Session = Depends(get_db)):
    """UPDATE: часткове оновлення профілю (username/email/пароль)."""
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "Користувача не знайдено")

    if payload.username and payload.username != user.username:
        if user_crud.get_user_by_username(db, payload.username):
            raise HTTPException(409, "Ім'я користувача вже зайняте")
    if payload.email and payload.email != user.email:
        if user_crud.get_user_by_email(db, payload.email):
            raise HTTPException(409, "Ця email-адреса вже використовується")

    return user_crud.update_user(db, user, payload)


@router.delete("/{user_id}", response_model=UserOut)
def delete_user(user_id: uuid.UUID, requester_id: uuid.UUID, db: Session = Depends(get_db)):
    """DELETE: м'яке видалення (is_active=False).

    Права доступу (роль): деактивувати акаунт може або сам власник
    (requester_id == user_id), або користувач з роллю 'admin'. Так
    реалізовано мінімальне розмежування прав "адмін / звичайний користувач".

    Фізичне видалення користувача навмисно не робиться, щоб не зруйнувати
    цілісність історії вже зіграних матчів (FK-обмеження на
    matches.coin_chooser_user_id / match_sides.user_id цього й не дозволять).
    """
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "Користувача не знайдено")

    if requester_id != user_id:
        _require_admin(db, requester_id)

    return user_crud.deactivate_user(db, user)


@router.post("/{user_id}/reactivate", response_model=UserOut)
def reactivate_user(user_id: uuid.UUID, requester_id: uuid.UUID, db: Session = Depends(get_db)):
    """Лише роль 'admin': повернути деактивований акаунт до активного стану."""
    _require_admin(db, requester_id)
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "Користувача не знайдено")
    return user_crud.reactivate_user(db, user)


@router.post("/{user_id}/promote", response_model=UserOut)
def promote_user(user_id: uuid.UUID, requester_id: uuid.UUID, db: Session = Depends(get_db)):
    """Лише роль 'admin': призначити іншого користувача адміністратором."""
    _require_admin(db, requester_id)
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "Користувача не знайдено")
    return user_crud.set_role(db, user, UserRole.admin)


@router.post("/{user_id}/demote", response_model=UserOut)
def demote_user(user_id: uuid.UUID, requester_id: uuid.UUID, db: Session = Depends(get_db)):
    """Лише роль 'admin': зняти права адміністратора (повернути роль 'user').
    Адмін не може зняти права сам із себе - щоб система не лишилась без жодного адміна."""
    _require_admin(db, requester_id)
    if requester_id == user_id:
        raise HTTPException(400, "Не можна зняти права адміністратора із самого себе")
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "Користувача не знайдено")
    return user_crud.set_role(db, user, UserRole.user)


@router.get("/{user_id}/rating/{mode}", response_model=PlayerRatingOut)
def get_user_rating(user_id: uuid.UUID, mode: GameMode, db: Session = Depends(get_db)):
    rating = rating_crud.get_player_rating(db, user_id, mode)
    if not rating:
        raise HTTPException(404, "Рейтинг не знайдено")

    out = PlayerRatingOut.model_validate(rating)
    # позицію у світовому рейтингу показуємо додатково лише гравцям рангу Diamond
    if is_top_rank(rating.rank):
        out.world_rank = rating_crud.get_world_rank_position(db, user_id, mode)
    return out