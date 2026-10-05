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
