"""
Бізнес-логіка гри "Орел/Решка":
- створення матчу (Solo 1х1 або Party 3х3)
- право вибору сторони монети надається стороні з нижчим MMR
- матч триває до 2 перемог в раундах (best_of=3)
- після завершення матчу перераховується MMR обох сторін
"""

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enums import CoinSide, GameMode, MatchStatus
from app.models.match import Match, MatchSide, Round
from app.models.rating import PlayerRating, RatingHistory
from app.models.team import Team, TeamMember
from app.services.elo import calculate_party_delta, calculate_solo_delta
from app.services.rank_service import resolve_rank


def _team_mmr_sum(db: Session, team_id: uuid.UUID, mode: GameMode) -> int:
    member_ids = [m.user_id for m in db.query(TeamMember).filter(TeamMember.team_id == team_id).all()]
    if len(member_ids) != 3:
        raise HTTPException(400, "Команда для Party-режиму повинна складатись рівно з 3 гравців")
    total = 0
    for uid in member_ids:
        rating = (
            db.query(PlayerRating)
            .filter(PlayerRating.user_id == uid, PlayerRating.mode == mode)
            .first()
        )
        total += rating.mmr if rating else 1000
    return total


def create_solo_match(db: Session, player1_id: uuid.UUID, player2_id: uuid.UUID) -> Match:
    r1 = db.query(PlayerRating).filter_by(user_id=player1_id, mode=GameMode.solo).first()
    r2 = db.query(PlayerRating).filter_by(user_id=player2_id, mode=GameMode.solo).first()
    if not r1 or not r2:
        raise HTTPException(404, "У одного з гравців відсутній Solo-рейтинг")

    match = Match(
        mode=GameMode.solo,
        status=MatchStatus.in_progress,
        best_of=3,
        side1_mmr_snapshot=r1.mmr,
        side2_mmr_snapshot=r2.mmr,
        # право вибору сторони монети - у гравця з нижчим MMR
        coin_chooser_user_id=player1_id if r1.mmr <= r2.mmr else player2_id,
    )
    db.add(match)
    try:
        db.flush()
        db.add(MatchSide(match_id=match.id, side=1, user_id=player1_id))
        db.add(MatchSide(match_id=match.id, side=2, user_id=player2_id))
        db.commit()
    except Exception:
        # Явний rollback: матч не повинен лишитись у БД без обох сторін
        # (наприклад, якщо player2_id виявиться некоректним FK).
        db.rollback()
        raise
    db.refresh(match)
    return match


def create_party_match(db: Session, team1_id: uuid.UUID, team2_id: uuid.UUID) -> Match:
    sum1 = _team_mmr_sum(db, team1_id, GameMode.party)
    sum2 = _team_mmr_sum(db, team2_id, GameMode.party)

    # обирає представник команди з нижчим сумарним MMR (перший учасник команди)
    lower_team_id = team1_id if sum1 <= sum2 else team2_id
    chooser = db.query(TeamMember).filter(TeamMember.team_id == lower_team_id).first()

    match = Match(
        mode=GameMode.party,
        status=MatchStatus.in_progress,
        best_of=3,
        side1_mmr_snapshot=sum1,
        side2_mmr_snapshot=sum2,
        coin_chooser_user_id=chooser.user_id,
    )
    db.add(match)
    try:
        db.flush()
        db.add(MatchSide(match_id=match.id, side=1, team_id=team1_id))
        db.add(MatchSide(match_id=match.id, side=2, team_id=team2_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(match)
    return match


def _busy_user_ids(db: Session) -> set[uuid.UUID]:
    """ID гравців, що вже перебувають у матчі зі статусом in_progress (Solo - напряму, Party - через команду)."""
    busy: set[uuid.UUID] = set()
    sides = (
        db.query(MatchSide)
        .join(Match, Match.id == MatchSide.match_id)
        .filter(Match.status == MatchStatus.in_progress)
        .all()
    )
    for s in sides:
        if s.user_id is not None:
            busy.add(s.user_id)
        if s.team_id is not None:
            for m in db.query(TeamMember).filter(TeamMember.team_id == s.team_id).all():
                busy.add(m.user_id)
    return busy


def _busy_team_ids(db: Session) -> set[uuid.UUID]:
    """ID команд, що вже перебувають у Party-матчі зі статусом in_progress."""
    sides = (
        db.query(MatchSide)
        .join(Match, Match.id == MatchSide.match_id)
        .filter(Match.status == MatchStatus.in_progress, MatchSide.team_id.isnot(None))
        .all()
    )
    return {s.team_id for s in sides}


def find_and_create_solo_match(db: Session, player_id: uuid.UUID) -> Match:
    """Швидкий пошук: серед вільних гравців з Solo-рейтингом обирає того, чий MMR найближчий
    до MMR заданого гравця, і одразу створює матч."""
    my_rating = db.query(PlayerRating).filter_by(user_id=player_id, mode=GameMode.solo).first()
    if not my_rating:
        raise HTTPException(404, "У гравця відсутній Solo-рейтинг")

    busy = _busy_user_ids(db) | {player_id}
    candidates = (
        db.query(PlayerRating)
        .filter(PlayerRating.mode == GameMode.solo, PlayerRating.user_id.notin_(busy))
        .all()
    )
    if not candidates:
        raise HTTPException(404, "Не знайдено вільних суперників для Solo-матчу")

    best = min(candidates, key=lambda r: abs(r.mmr - my_rating.mmr))
    return create_solo_match(db, player_id, best.user_id)


def find_and_create_party_match(db: Session, team_id: uuid.UUID) -> Match:
    """Швидкий пошук: серед вільних команд обирає ту, чий сумарний MMR найближчий
    до сумарного MMR заданої команди, і одразу створює Party-матч."""
    my_sum = _team_mmr_sum(db, team_id, GameMode.party)

    busy = _busy_team_ids(db) | {team_id}
    other_team_ids = [t.id for t in db.query(Team).filter(Team.id.notin_(busy)).all()]
    if not other_team_ids:
        raise HTTPException(404, "Не знайдено вільних команд-суперників для Party-матчу")

    best_team_id, best_diff = None, None
    for tid in other_team_ids:
        try:
            s = _team_mmr_sum(db, tid, GameMode.party)
        except HTTPException:
            continue  # пропускаємо команди, що не мають рівно 3 учасників
        diff = abs(s - my_sum)
        if best_diff is None or diff < best_diff:
            best_team_id, best_diff = tid, diff

    if best_team_id is None:
        raise HTTPException(404, "Не знайдено вільних команд-суперників для Party-матчу")

    return create_party_match(db, team_id, best_team_id)


def submit_round(db: Session, match_id: uuid.UUID, coin_choice: CoinSide) -> Round:
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(404, "Матч не знайдено")
    if match.status != MatchStatus.in_progress:
        raise HTTPException(400, "Матч не в статусі 'in_progress'")

    existing_rounds = db.query(Round).filter(Round.match_id == match_id).order_by(Round.round_number).all()
    wins_side1 = sum(1 for r in existing_rounds if r.winner_side == 1)
    wins_side2 = sum(1 for r in existing_rounds if r.winner_side == 2)
    needed_wins = match.best_of // 2 + 1  # best_of=3 -> 2 перемоги

    if wins_side1 >= needed_wins or wins_side2 >= needed_wins:
        raise HTTPException(400, "Матч уже завершено")

    # Сторона, що обирала (coin_chooser) - завжди сторона 1 чи 2? Визначаємо динамічно:
    chooser_side = _side_of_user(db, match, match.coin_chooser_user_id)

    # Результат підкидання визначає СЕРВЕР випадково (secrets - криптографічно стійкий
    # генератор), а не клієнт: інакше гравець міг би передати "вигідний" собі coin_result
    # і заздалегідь визначати переможця матчу.
    coin_result = secrets.choice([CoinSide.heads, CoinSide.tails])

    # Якщо вибір співпав з результатом підкидання - вигравець стороны, що обирала.
    round_winner_side = chooser_side if coin_choice == coin_result else _other_side(chooser_side)

    round_number = len(existing_rounds) + 1
    round_obj = Round(
        match_id=match_id,
        round_number=round_number,
        coin_choice=coin_choice,
        coin_result=coin_result,
        winner_side=round_winner_side,
    )
    db.add(round_obj)

    # Перерахунок перемог з урахуванням нового раунду
    if round_winner_side == 1:
        wins_side1 += 1
    else:
        wins_side2 += 1

    try:
        if wins_side1 >= needed_wins or wins_side2 >= needed_wins:
            match.status = MatchStatus.finished
            match.winner_side = 1 if wins_side1 > wins_side2 else 2
            match.finished_at = datetime.now(timezone.utc)
            db.add(match)
            db.flush()
            # _apply_rating_changes пише в player_ratings ТА rating_history одразу
            # для кількох гравців (Party - до 6 записів). Якщо тут щось піде не так
            # (наприклад, гравця видалили і PlayerRating не знайдено) - відкочуємо
            # усю транзакцію разом з уже доданим раундом, щоб не лишити матч
            # у суперечливому стані "завершено, але MMR не перераховано".
            _apply_rating_changes(db, match)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(round_obj)
    return round_obj


def cancel_match(db: Session, match_id: uuid.UUID) -> Match:
    """UPDATE: скасування матчу, поки в ньому не зіграно жодного раунду
    (інакше довелося б відкочувати вже нараховані перемоги в раундах)."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(404, "Матч не знайдено")
    if match.status not in (MatchStatus.pending, MatchStatus.in_progress):
        raise HTTPException(400, f"Матч у статусі '{match.status.value}' не можна скасувати")

    played_rounds = db.query(Round).filter(Round.match_id == match_id).count()
    if played_rounds > 0:
        raise HTTPException(400, "Не можна скасувати матч, у якому вже зіграно раунди")

    match.status = MatchStatus.cancelled
    match.finished_at = datetime.now(timezone.utc)
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def delete_match(db: Session, match_id: uuid.UUID) -> None:
    """DELETE: фізичне видалення матчу - лише якщо він скасований або ще не мав
    зіграних раундів. Завершені матчі (finished) видаляти не можна - вони є
    джерелом для rating_history (ON DELETE SET NULL), і їхнє видалення зробило б
    історію зміни MMR "осиротілою"."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(404, "Матч не знайдено")

    played_rounds = db.query(Round).filter(Round.match_id == match_id).count()
    removable = match.status == MatchStatus.cancelled or (
        match.status in (MatchStatus.pending, MatchStatus.in_progress) and played_rounds == 0
    )
    if not removable:
        raise HTTPException(409, "Видалити можна лише скасований матч або матч без зіграних раундів")

    try:
        db.delete(match)  # cascade видалить match_sides/rounds (ON DELETE CASCADE)
        db.commit()
    except Exception:
        db.rollback()
        raise


def _side_of_user(db: Session, match: Match, user_id: uuid.UUID) -> int:
    """Визначає, якій стороні (1/2) належить конкретний user_id (для Party - через його команду)."""
    sides = db.query(MatchSide).filter(MatchSide.match_id == match.id).all()
    for s in sides:
        if s.user_id == user_id:
            return s.side
        if s.team_id is not None:
            member = (
                db.query(TeamMember)
                .filter(TeamMember.team_id == s.team_id, TeamMember.user_id == user_id)
                .first()
            )
            if member:
                return s.side
    raise HTTPException(400, "Не вдалось визначити сторону гравця, що обирає монету")


def _other_side(side: int) -> int:
    return 2 if side == 1 else 1


def _apply_rating_changes(db: Session, match: Match) -> None:
    """Оновлює MMR, ранг та історію рейтингу після завершення матчу."""
    sides = {s.side: s for s in db.query(MatchSide).filter(MatchSide.match_id == match.id).all()}
    winner_side, loser_side = match.winner_side, _other_side(match.winner_side)

    if match.mode == GameMode.solo:
        winner_user_ids = [sides[winner_side].user_id]
        loser_user_ids = [sides[loser_side].user_id]
        winner_mmr_ref = match.side1_mmr_snapshot if winner_side == 1 else match.side2_mmr_snapshot
        loser_mmr_ref = match.side1_mmr_snapshot if loser_side == 1 else match.side2_mmr_snapshot

        winner_rank = resolve_rank(db, GameMode.solo, winner_mmr_ref)
        loser_rank = resolve_rank(db, GameMode.solo, loser_mmr_ref)
        deltas = calculate_solo_delta(
            winner_mmr_ref, loser_mmr_ref,
            winner_rank.name if winner_rank else None,
            loser_rank.name if loser_rank else None,
        )
        _update_player(db, winner_user_ids[0], GameMode.solo, deltas.delta_winner, match.id, is_win=True)
        _update_player(db, loser_user_ids[0], GameMode.solo, deltas.delta_loser, match.id, is_win=False)

    else:  # party
        winner_team_id = sides[winner_side].team_id
        loser_team_id = sides[loser_side].team_id
        winner_sum = match.side1_mmr_snapshot if winner_side == 1 else match.side2_mmr_snapshot
        loser_sum = match.side1_mmr_snapshot if loser_side == 1 else match.side2_mmr_snapshot

        winner_rank = resolve_rank(db, GameMode.party, winner_sum // 3)
        loser_rank = resolve_rank(db, GameMode.party, loser_sum // 3)
        deltas = calculate_party_delta(
            winner_sum, loser_sum,
            winner_rank.name if winner_rank else None,
            loser_rank.name if loser_rank else None,
        )

        winner_members = db.query(TeamMember).filter(TeamMember.team_id == winner_team_id).all()
        loser_members = db.query(TeamMember).filter(TeamMember.team_id == loser_team_id).all()

        for m in winner_members:
            _update_player(db, m.user_id, GameMode.party, deltas.delta_winner, match.id, is_win=True)
        for m in loser_members:
            _update_player(db, m.user_id, GameMode.party, deltas.delta_loser, match.id, is_win=False)


def _update_player(db: Session, user_id: uuid.UUID, mode: GameMode, delta: int, match_id: uuid.UUID, is_win: bool) -> None:
    rating = db.query(PlayerRating).filter_by(user_id=user_id, mode=mode).first()
    if not rating:
        return

    mmr_before = rating.mmr
    mmr_after = max(0, mmr_before + delta)  # MMR не йде нижче 0

    rating.mmr = mmr_after
    rating.matches_played += 1
    if is_win:
        rating.wins += 1
    else:
        rating.losses += 1

    new_rank = resolve_rank(db, mode, mmr_after)
    rating.rank_id = new_rank.id if new_rank else None

    db.add(rating)
    db.add(
        RatingHistory(
            user_id=user_id,
            mode=mode,
            match_id=match_id,
            mmr_before=mmr_before,
            mmr_after=mmr_after,
            delta=mmr_after - mmr_before,
        )
    )