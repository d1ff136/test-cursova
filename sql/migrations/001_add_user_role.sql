-- ============================================================
-- Міграція: додає роль користувача (user/admin) до ВЖЕ ІСНУЮЧОЇ
-- таблиці users, не чіпаючи наявні дані (users, matches, rounds...).
--
-- Потрібна, якщо БД була створена зі старішої версії sql/schema.sql
-- (до того, як з'явилась колонка role) - симптом: помилка
-- "psycopg.errors.UndefinedColumn: стовпець users.role не існує".
--
-- Застосувати:
--   psql -U mmr_user -d mmr_db -f sql/migrations/001_add_user_role.sql
-- (або виконати цей текст просто в консолі DataGrip)
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('user', 'admin');
    END IF;
END$$;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS role user_role NOT NULL DEFAULT 'user';

-- За бажанням: зробити конкретного існуючого користувача адміном
-- (підставте свій реальний username замість 'arthur'):
-- UPDATE users SET role = 'admin' WHERE username = 'arthur';
