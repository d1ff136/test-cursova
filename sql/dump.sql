-- ============================================================
-- ПОВНИЙ ДАМП БАЗИ ДАНИХ: структура + приклад даних (seed)
-- Гра "Орел/Решка" - MMR та матчмейкінг (Solo 1х1 / Party 3х3)
-- PostgreSQL 14+
--
-- Відтворення з нуля:
--   createdb mmr_db
--   psql mmr_db -f sql/dump.sql
--
-- Цей файл = sql/schema.sql + sql/seed_ranks.sql + приклад даних нижче,
-- зібрані в один самодостатній дамп (аналог виводу pg_dump), щоб можна
-- було підняти повністю робочу БД з прикладними записами одним запуском.
-- ============================================================

-- ############################################################
-- ЧАСТИНА 1. СХЕМА (див. також окремо sql/schema.sql)
-- ############################################################

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


-- ############################################################
-- ЧАСТИНА 2. ДОВІДНИК РАНГІВ (див. також окремо sql/seed_ranks.sql)
-- ############################################################
-- ============================================================
-- Початкове наповнення довідника рангів.
-- Однакова шкала для 'solo' та 'party' .
-- Bronze/Silver/Gold мають рівні 1-3, Diamond — єдиний топ-ранг.
-- ============================================================

DO $$
DECLARE
    m game_mode;
BEGIN
    FOREACH m IN ARRAY ARRAY['solo', 'party']::game_mode[] LOOP
        INSERT INTO ranks (mode, name, tier, min_mmr, max_mmr, sort_order) VALUES
            (m, 'Bronze',   1,    0,  499, 1),
            (m, 'Bronze',   2,  500,  799, 2),
            (m, 'Bronze',   3,  800, 1099, 3),
            (m, 'Silver',   1, 1100, 1399, 4),
            (m, 'Silver',   2, 1400, 1699, 5),
            (m, 'Silver',   3, 1700, 1999, 6),
            (m, 'Gold',     1, 2000, 2299, 7),
            (m, 'Gold',     2, 2300, 2599, 8),
            (m, 'Gold',     3, 2600, 2899, 9),
            (m, 'Diamond',  NULL, 2900, NULL, 10);
    END LOOP;
END $$;


-- ############################################################
-- ЧАСТИНА 3. ПРИКЛАДНІ ДАНІ (SEED) - демонстраційний набір
--   8 гравців, 2 постійні Party-команди, 1 завершений Solo-матч,
--   1 завершений Party-матч (з раундами й перерахованим MMR).
--
-- УВАГА: password_hash нижче - синтаксично коректні за форматом,
-- але НЕ робочі bcrypt-хеші (згенеровані вручну для прикладу, без
-- реального застосунку passlib). Логін через API під цими акаунтами
-- не спрацює - для тестового входу зареєструйте користувача через
-- POST /users/, щоб бекенд порахував справжній bcrypt-хеш.
-- ############################################################

-- ------------------------------------------------------------
-- 3.1. Користувачі (arthur - адміністратор, решта - звичайні гравці)
-- ------------------------------------------------------------
INSERT INTO users (id, username, email, password_hash, role, is_active, created_at) VALUES
    ('11111111-1111-4111-8111-111111111101', 'arthur',    'arthur@example.com',    '$2b$12$demoSeedHashNotRealBcryptHash0000000001', 'admin', TRUE, now() - interval '30 days'),
    ('11111111-1111-4111-8111-111111111102', 'beatrice',  'beatrice@example.com',  '$2b$12$demoSeedHashNotRealBcryptHash0000000002', 'user',  TRUE, now() - interval '29 days'),
    ('11111111-1111-4111-8111-111111111103', 'carter',    'carter@example.com',    '$2b$12$demoSeedHashNotRealBcryptHash0000000003', 'user',  TRUE, now() - interval '28 days'),
    ('11111111-1111-4111-8111-111111111104', 'diana',     'diana@example.com',     '$2b$12$demoSeedHashNotRealBcryptHash0000000004', 'user',  TRUE, now() - interval '27 days'),
    ('11111111-1111-4111-8111-111111111105', 'ethan',     'ethan@example.com',     '$2b$12$demoSeedHashNotRealBcryptHash0000000005', 'user',  TRUE, now() - interval '26 days'),
    ('11111111-1111-4111-8111-111111111106', 'fiona',     'fiona@example.com',     '$2b$12$demoSeedHashNotRealBcryptHash0000000006', 'user',  TRUE, now() - interval '25 days'),
    ('11111111-1111-4111-8111-111111111107', 'gabriel',   'gabriel@example.com',   '$2b$12$demoSeedHashNotRealBcryptHash0000000007', 'user',  TRUE, now() - interval '24 days'),
    ('11111111-1111-4111-8111-111111111108', 'helena',    'helena@example.com',    '$2b$12$demoSeedHashNotRealBcryptHash0000000008', 'user',  TRUE, now() - interval '23 days');

-- ------------------------------------------------------------
-- 3.2. Стартові рейтинги (Solo + Party, по 1000 MMR для кожного)
-- ------------------------------------------------------------
INSERT INTO player_ratings (user_id, mode, mmr)
SELECT id, mode, 1000
FROM users, unnest(ARRAY['solo', 'party']::game_mode[]) AS mode
WHERE username IN ('arthur','beatrice','carter','diana','ethan','fiona','gabriel','helena');

-- ------------------------------------------------------------
-- 3.3. Команди (Party, постійні паті)
-- ------------------------------------------------------------
INSERT INTO teams (id, name, is_permanent, created_at) VALUES
    ('22222222-2222-4222-8222-222222222201', 'Нічна варта', TRUE, now() - interval '20 days'),
    ('22222222-2222-4222-8222-222222222202', 'Червоні леви', TRUE, now() - interval '18 days');

INSERT INTO team_members (team_id, user_id) VALUES
    ('22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111101'), -- arthur
    ('22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111102'), -- beatrice
    ('22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111103'), -- carter
    ('22222222-2222-4222-8222-222222222202', '11111111-1111-4111-8111-111111111104'), -- diana
    ('22222222-2222-4222-8222-222222222202', '11111111-1111-4111-8111-111111111105'), -- ethan
    ('22222222-2222-4222-8222-222222222202', '11111111-1111-4111-8111-111111111106'); -- fiona

-- ------------------------------------------------------------
-- 3.4. Завершений Solo-матч: gabriel (1000 MMR) проти helena (1000 MMR)
--      gabriel обирав сторону монети (рівний MMR -> перший зі сторін).
--      Рахунок 2:1 на користь gabriel.
-- ------------------------------------------------------------
INSERT INTO matches (id, mode, status, best_of, side1_mmr_snapshot, side2_mmr_snapshot,
                      coin_chooser_user_id, winner_side, created_at, finished_at) VALUES
    ('33333333-3333-4333-8333-333333333301', 'solo', 'finished', 3, 1000, 1000,
     '11111111-1111-4111-8111-111111111107', 1,
     now() - interval '10 days', now() - interval '10 days' + interval '6 minutes');

INSERT INTO match_sides (match_id, side, user_id) VALUES
    ('33333333-3333-4333-8333-333333333301', 1, '11111111-1111-4111-8111-111111111107'), -- gabriel
    ('33333333-3333-4333-8333-333333333301', 2, '11111111-1111-4111-8111-111111111108'); -- helena

INSERT INTO rounds (match_id, round_number, coin_choice, coin_result, winner_side, created_at) VALUES
    ('33333333-3333-4333-8333-333333333301', 1, 'heads', 'heads', 1, now() - interval '10 days' + interval '1 minute'),
    ('33333333-3333-4333-8333-333333333301', 2, 'tails', 'heads', 2, now() - interval '10 days' + interval '3 minutes'),
    ('33333333-3333-4333-8333-333333333301', 3, 'heads', 'heads', 1, now() - interval '10 days' + interval '6 minutes');

-- Перерахунок MMR після матчу (ілюстративні дельти +18 / -18, як приклад Elo-подібної формули)
UPDATE player_ratings SET mmr = 1018, wins = 1, matches_played = 1, updated_at = now() - interval '10 days'
WHERE user_id = '11111111-1111-4111-8111-111111111107' AND mode = 'solo';
UPDATE player_ratings SET mmr = 982, losses = 1, matches_played = 1, updated_at = now() - interval '10 days'
WHERE user_id = '11111111-1111-4111-8111-111111111108' AND mode = 'solo';

INSERT INTO rating_history (user_id, mode, match_id, mmr_before, mmr_after, delta, created_at) VALUES
    ('11111111-1111-4111-8111-111111111107', 'solo', '33333333-3333-4333-8333-333333333301', 1000, 1018,  18, now() - interval '10 days'),
    ('11111111-1111-4111-8111-111111111108', 'solo', '33333333-3333-4333-8333-333333333301', 1000,  982, -18, now() - interval '10 days');

-- ------------------------------------------------------------
-- 3.5. Завершений Party-матч: "Нічна варта" (3000 MMR) проти "Червоні леви" (3000 MMR)
--      Рахунок 2:0 на користь "Нічної варти".
-- ------------------------------------------------------------
INSERT INTO matches (id, mode, status, best_of, side1_mmr_snapshot, side2_mmr_snapshot,
                      coin_chooser_user_id, winner_side, created_at, finished_at) VALUES
    ('33333333-3333-4333-8333-333333333302', 'party', 'finished', 3, 3000, 3000,
     '11111111-1111-4111-8111-111111111101', 1,
     now() - interval '5 days', now() - interval '5 days' + interval '8 minutes');

INSERT INTO match_sides (match_id, side, team_id) VALUES
    ('33333333-3333-4333-8333-333333333302', 1, '22222222-2222-4222-8222-222222222201'), -- Нічна варта
    ('33333333-3333-4333-8333-333333333302', 2, '22222222-2222-4222-8222-222222222202'); -- Червоні леви

INSERT INTO rounds (match_id, round_number, coin_choice, coin_result, winner_side, created_at) VALUES
    ('33333333-3333-4333-8333-333333333302', 1, 'tails', 'tails', 1, now() - interval '5 days' + interval '2 minutes'),
    ('33333333-3333-4333-8333-333333333302', 2, 'tails', 'tails', 1, now() - interval '5 days' + interval '8 minutes');

-- Перерахунок MMR для всіх 6 учасників (по +15 переможцям / -15 переможеним, ілюстративно)
UPDATE player_ratings SET mmr = 1015, wins = 1, matches_played = 1, updated_at = now() - interval '5 days'
WHERE mode = 'party' AND user_id IN (
    '11111111-1111-4111-8111-111111111101',
    '11111111-1111-4111-8111-111111111102',
    '11111111-1111-4111-8111-111111111103'
);
UPDATE player_ratings SET mmr = 985, losses = 1, matches_played = 1, updated_at = now() - interval '5 days'
WHERE mode = 'party' AND user_id IN (
    '11111111-1111-4111-8111-111111111104',
    '11111111-1111-4111-8111-111111111105',
    '11111111-1111-4111-8111-111111111106'
);

INSERT INTO rating_history (user_id, mode, match_id, mmr_before, mmr_after, delta, created_at)
SELECT user_id, 'party'::game_mode, '33333333-3333-4333-8333-333333333302'::uuid, 1000, 1015, 15, now() - interval '5 days'
FROM unnest(ARRAY[
    '11111111-1111-4111-8111-111111111101',
    '11111111-1111-4111-8111-111111111102',
    '11111111-1111-4111-8111-111111111103'
]::uuid[]) AS user_id
UNION ALL
SELECT user_id, 'party'::game_mode, '33333333-3333-4333-8333-333333333302'::uuid, 1000, 985, -15, now() - interval '5 days'
FROM unnest(ARRAY[
    '11111111-1111-4111-8111-111111111104',
    '11111111-1111-4111-8111-111111111105',
    '11111111-1111-4111-8111-111111111106'
]::uuid[]) AS user_id;



-- ------------------------------------------------------------
-- 3.6. Проставити ранг (rank_id) відповідно до підсумкового MMR
--      (в API це робить app/services/rank_service.py після кожного матчу)
-- ------------------------------------------------------------
UPDATE player_ratings pr
SET rank_id = r.id
FROM ranks r
WHERE r.mode = pr.mode
  AND pr.mmr BETWEEN r.min_mmr AND COALESCE(r.max_mmr, 999999);
