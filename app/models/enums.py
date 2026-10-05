import enum


class GameMode(str, enum.Enum):
    solo = "solo"
    party = "party"


class MatchStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    finished = "finished"
    cancelled = "cancelled"


class CoinSide(str, enum.Enum):
    heads = "heads"   # Орел
    tails = "tails"   # Решка


class UserRole(str, enum.Enum):
    user = "user"      # звичайний гравець
    admin = "admin"     # може деактивувати/реактивувати інших користувачів,
                        # призначати нових адмінів