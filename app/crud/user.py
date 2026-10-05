import uuid

import bcrypt
from sqlalchemy.orm import Session

from app.models.enums import GameMode, UserRole
from app.models.rating import PlayerRating
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

# bcrypt-хешування напряму (без passlib): passlib 1.7.4 не оновлювалась з 2020 року
# і ламається на сучасних версіях бібліотеки bcrypt (>=4.1) через власний
# внутрішній самотест - див. https://github.com/pyca/bcrypt/issues/684.
# Сіль генерується й вбудовується автоматично в сам хеш (формат $2b$12$...),
# тому окрема колонка для солі не потрібна.
_BCRYPT_MAX_BYTES = 72  # жорсткий ліміт самого алгоритму bcrypt


def _hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Порівняння пароля з хешем. bcrypt.checkpw сам виконує це у постійний
    час (захист від timing-атак)."""
    try:
        pw_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw_bytes, password_hash.encode("ascii"))
    except (ValueError, TypeError):
        # хеш у нерозпізнаваному форматі (напр. старий SHA256-запис) - вважаємо невалідним
        return False


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Перевіряє логін/пароль. Повертає User при успіху, інакше None."""
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=_hash_password(payload.password),
    )
    db.add(user)
    db.flush()  # отримати user.id до commit

    # Одразу створюємо стартовий рейтинг 1000 MMR для обох режимів.
    for mode in (GameMode.solo, GameMode.party):
        db.add(PlayerRating(user_id=user.id, mode=mode, mmr=1000))

    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    """UPDATE: часткове оновлення профілю (username/email/пароль)."""
    if payload.username is not None:
        user.username = payload.username
    if payload.email is not None:
        user.email = payload.email
    if payload.password is not None:
        user.password_hash = _hash_password(payload.password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user: User) -> User:
    """"Видалення" акаунта - м'яке (is_active=False), а не фізичне DELETE.

    Фізичне видалення заблоковане на рівні БД (FK matches.coin_chooser_user_id
    та match_sides.user_id не мають ON DELETE CASCADE) саме для того, щоб не можна
    було стерти гравця, що вже брав участь у зіграних матчах, і тим самим
    зіпсувати історію матчів/рейтингу. Деактивований користувач не є видимим
    для нових матчів, але його історія лишається цілою.
    """
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reactivate_user(db: Session, user: User) -> User:
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def is_admin(user: User | None) -> bool:
    return user is not None and user.role == UserRole.admin and user.is_active


def set_role(db: Session, user: User, role: UserRole) -> User:
    """Призначення/зняття ролі адміністратора. Викликач (router) відповідає
    за те, щоб requester сам був активним адміном - див. routers/users.py."""
    user.role = role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user