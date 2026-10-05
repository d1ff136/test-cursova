"""
Розрахунок зміни MMR за Elo-подібною формулою.

Ідея: очікуваний результат гравця/команди A залежить від різниці MMR
з суперником B:

    expected_A = 1 / (1 + 10 ^ ((mmr_B - mmr_A) / scale))

Реальний результат actual_A = 1 (перемога) або 0 (поразка).

    delta_A = round(K * (actual_A - expected_A))

Якщо A слабший (нижчий MMR) і перемагає -> expected_A < 0.5 -> delta більший.
Якщо A сильніший і перемагає -> expected_A > 0.5 -> delta менший.
Це саме та "збалансованість", яку описано в ТЗ.

Для Party-режиму порівнюються СУМИ MMR команд (3 гравці), тому масштаб
(scale) множимо на кількість гравців у команді, аби різниця сум давала
приблизно такий самий ефект, як і різниця індивідуальних MMR у Solo.
"""

from dataclasses import dataclass

from app.models.enums import GameMode

SOLO_SCALE = 400
PARTY_TEAM_SIZE = 3
PARTY_SCALE = SOLO_SCALE * PARTY_TEAM_SIZE

# K-фактор залежить від рангу: нижчі ранги "гойдаються" сильніше,
# щоб новачки швидше знайшли свій рівень; топові ранги змінюються повільніше.
K_FACTOR_BY_RANK_NAME = {
    "Bronze": 40,
    "Silver": 35,
    "Gold": 30,
    "Diamond": 20,
}
DEFAULT_K_FACTOR = 32


def get_k_factor(rank_name: str | None) -> int:
    if rank_name is None:
        return DEFAULT_K_FACTOR
    return K_FACTOR_BY_RANK_NAME.get(rank_name, DEFAULT_K_FACTOR)


def expected_score(own_mmr: int, opponent_mmr: int, scale: int) -> float:
    return 1.0 / (1.0 + 10 ** ((opponent_mmr - own_mmr) / scale))


@dataclass
class RatingDelta:
    delta_winner: int
    delta_loser: int


def calculate_solo_delta(
    winner_mmr: int,
    loser_mmr: int,
    winner_rank_name: str | None,
    loser_rank_name: str | None,
) -> RatingDelta:
    """Зміна MMR для Solo-матчу (1х1)."""
    exp_winner = expected_score(winner_mmr, loser_mmr, SOLO_SCALE)
    exp_loser = expected_score(loser_mmr, winner_mmr, SOLO_SCALE)

    k_winner = get_k_factor(winner_rank_name)
    k_loser = get_k_factor(loser_rank_name)

    delta_winner = round(k_winner * (1 - exp_winner))
    delta_loser = round(k_loser * (0 - exp_loser))

    # Переможець завжди отримує щонайменше 1 очко, переможений - втрачає щонайменше 1.
    delta_winner = max(delta_winner, 1)
    delta_loser = min(delta_loser, -1)

    return RatingDelta(delta_winner=delta_winner, delta_loser=delta_loser)


def calculate_party_delta(
    winner_team_mmr_sum: int,
    loser_team_mmr_sum: int,
    winner_rank_name: str | None,
    loser_rank_name: str | None,
) -> RatingDelta:
    """
    Зміна MMR для Party-матчу (3х3). Однакова дельта застосовується
    до кожного гравця виграшної/програшної команди (спрощена модель;
    легко замінити на зважену за індивідуальним MMR гравця).
    """
    exp_winner = expected_score(winner_team_mmr_sum, loser_team_mmr_sum, PARTY_SCALE)
    exp_loser = expected_score(loser_team_mmr_sum, winner_team_mmr_sum, PARTY_SCALE)

    k_winner = get_k_factor(winner_rank_name)
    k_loser = get_k_factor(loser_rank_name)

    delta_winner = round(k_winner * (1 - exp_winner))
    delta_loser = round(k_loser * (0 - exp_loser))

    delta_winner = max(delta_winner, 1)
    delta_loser = min(delta_loser, -1)

    return RatingDelta(delta_winner=delta_winner, delta_loser=delta_loser)
