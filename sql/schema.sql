-- ============================================================
-- Схема бази даних: система рейтингів та матчмейкінгу
-- гри "Орел/Решка" (Solo MMR + Party MMR)
-- PostgreSQL 14+
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- для gen_random_uuid()

-- ------------------------------------------------------------
-- ENUM-типи
-- ------------------------------------------------------------
CREATE TYPE game_mode AS ENUM ('solo', 'party');
CREATE TYPE match_status AS ENUM ('pending', 'in_progress', 'finished', 'cancelled');
CREATE TYPE coin_side AS ENUM ('heads', 'tails');           -- Орел / Решка
CREATE TYPE user_role AS ENUM ('user', 'admin');

-- ------------------------------------------------------------
-- 1. Користувачі
-- ------------------------------------------------------------
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      VARCHAR(32)  NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          user_role    NOT NULL DEFAULT 'user',
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 2. Ранги (довідник), окремо для кожного режиму,
--    з поділом на рівні (Bronze 1-3, Silver 1-3, Gold 1-3, Diamond)
-- ------------------------------------------------------------
CREATE TABLE ranks (
    id         SERIAL PRIMARY KEY,
    mode       game_mode   NOT NULL,
    name       VARCHAR(32) NOT NULL,          -- Bronze / Silver / Gold / Diamond
    tier       SMALLINT,                      -- 1..3, NULL для Diamond (єдиний рівень)
    min_mmr    INTEGER     NOT NULL,
    max_mmr    INTEGER,                       -- NULL = без верхньої межі (Diamond)
    sort_order INTEGER     NOT NULL,          -- для впорядкування Bronze1 < ... < Diamond
    UNIQUE (mode, name, tier),
    UNIQUE (mode, sort_order),
    CHECK (max_mmr IS NULL OR max_mmr > min_mmr)
);

-- ------------------------------------------------------------
-- 3. Рейтинг гравця (окремо Solo/Party)
-- ------------------------------------------------------------
CREATE TABLE player_ratings (
    id             BIGSERIAL PRIMARY KEY,
    user_id        UUID       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode           game_mode  NOT NULL,
    mmr            INTEGER    NOT NULL DEFAULT 1000,
    rank_id        INTEGER    REFERENCES ranks(id),
    wins           INTEGER    NOT NULL DEFAULT 0,
    losses         INTEGER    NOT NULL DEFAULT 0,
    matches_played INTEGER    NOT NULL DEFAULT 0,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, mode)
);
CREATE INDEX idx_player_ratings_mode_mmr ON player_ratings (mode, mmr DESC);

-- ------------------------------------------------------------
-- 4. Команди (для Party-режиму, тимчасові або постійні "паті")
-- ------------------------------------------------------------
CREATE TABLE teams (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         VARCHAR(64),
    is_permanent BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE team_members (
    id        BIGSERIAL PRIMARY KEY,
    team_id   UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (team_id, user_id)
);

-- ------------------------------------------------------------
-- 5. Матчі
-- ------------------------------------------------------------
CREATE TABLE matches (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode                game_mode    NOT NULL,
    status              match_status NOT NULL DEFAULT 'pending',
    best_of             SMALLINT     NOT NULL DEFAULT 3,   -- перемога до 2 перемог
    side1_mmr_snapshot  INTEGER,                           -- MMR (сума для party) на старті
    side2_mmr_snapshot  INTEGER,
    coin_chooser_user_id UUID REFERENCES users(id),        -- обирає гравець зі стороною нижчого MMR
    winner_side         SMALLINT CHECK (winner_side IN (1, 2)),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ
);

-- Сторони матчу: у Solo — гравець, у Party — команда
CREATE TABLE match_sides (
    id          BIGSERIAL PRIMARY KEY,
    match_id    UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    side        SMALLINT NOT NULL CHECK (side IN (1, 2)),
    user_id     UUID REFERENCES users(id),
    team_id     UUID REFERENCES teams(id),
    UNIQUE (match_id, side),
    CHECK ( (user_id IS NOT NULL AND team_id IS NULL)
         OR (user_id IS NULL AND team_id IS NOT NULL) )
);

-- ------------------------------------------------------------
-- 6. Раунди матчу (кожен матч = серія раундів "Орел/Решка")
-- ------------------------------------------------------------
CREATE TABLE rounds (
    id           BIGSERIAL PRIMARY KEY,
    match_id     UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    round_number SMALLINT NOT NULL,
    coin_choice  coin_side NOT NULL,   -- що обрав гравець з нижчим MMR
    coin_result  coin_side NOT NULL,   -- фактичний результат підкидання
    winner_side  SMALLINT NOT NULL CHECK (winner_side IN (1, 2)),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (match_id, round_number)
);

-- ------------------------------------------------------------
-- 7. Історія зміни рейтингу
-- ------------------------------------------------------------
CREATE TABLE rating_history (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode        game_mode NOT NULL,
    match_id    UUID REFERENCES matches(id) ON DELETE SET NULL,
    mmr_before  INTEGER NOT NULL,
    mmr_after   INTEGER NOT NULL,
    delta       INTEGER NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_rating_history_user_mode ON rating_history (user_id, mode, created_at DESC);

-- ------------------------------------------------------------
-- Початкові ранги (seed) — див. sql/seed_ranks.sql
-- ------------------------------------------------------------