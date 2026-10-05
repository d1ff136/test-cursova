# Повний посібник з налаштування проєкту MMR

Цей посібник допоможе вам встановити PostgreSQL, створити базу даних та запустити систему рейтингів для гри "Орел/Решка".

## Крок 1: Встановлення PostgreSQL

### Для Windows

1. **Завантажте PostgreSQL**
   - Перейдіть на офіційний сайт: https://www.postgresql.org/download/windows/
   - Завантажте інсталятор PostgreSQL (рекомендується версія 14 або новіша)
   - Або використайте прямий лінк: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

2. **Запустіть інсталятор**
   - Двічі клацніть на завантажений файл `.exe`
   - Натисніть "Next" на екрані привітання

3. **Виберіть директорію встановлення**
   - Залиште за замовчуванням або оберіть свою директорію
   - Натисніть "Next"

4. **Виберіть компоненти**
   - Переконайтеся, що обрані:
     - ✅ PostgreSQL Server
     - ✅ pgAdmin 4 (графічний інтерфейс)
     - ✅ Command Line Tools (важливо!)
   - Натисніть "Next"

5. **Виберіть директорію для даних**
   - Залиште за замовчуванням (зазвичай `C:\Program Files\PostgreSQL\16\data`)
   - Натисніть "Next"

6. **Встановіть пароль суперкористувача**
   - Введіть пароль для користувача `postgres` (запам'ятайте його!)
   - Підтвердіть пароль
   - Натисніть "Next"

7. **Виберіть порт**
   - Залиште порт за замовчуванням: `5432`
   - Натисніть "Next"

8. **Виберіть локаль**
   - Оберіть локаль (наприклад, "Ukrainian, Ukraine" або "Default locale")
   - Натисніть "Next"

9. **Завершіть установку**
   - Натисніть "Next" → "Next" → "Finish"

10. **Додайте PostgreSQL до PATH (важливо!)**
    - Натисніть `Win + R`, введіть `sysdm.cpl` і натисніть Enter
    - Перейдіть на вкладку "Advanced" → "Environment Variables"
    - У розділі "System variables" знайдіть змінну `Path` і натисніть "Edit"
    - Натисніть "New" і додайте шлях до PostgreSQL bin:
      ```
      C:\Program Files\PostgreSQL\16\bin
      ```
    - Натисніть "OK" → "OK" → "OK"
    - **Перезапустіть командний рядок або Git Bash**, щоб зміни набули чинності

11. **Перевірте установку**
    ```bash
    # Відкрийте новий термінал Git Bash і введіть:
    psql --version
    ```
    Ви повинні побачити щось на зразок: `psql (PostgreSQL) 16.x`

### Для macOS

```bash
# Використовуючи Homebrew
brew install postgresql@16

# Запустіть PostgreSQL
brew services start postgresql@16

# Додайте до PATH (якщо потрібно)
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Для Linux (Ubuntu/Debian)

```bash
# Оновіть пакети
sudo apt update

# Встановіть PostgreSQL
sudo apt install postgresql postgresql-contrib

# Запустіть службу
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## Крок 2: Налаштування PostgreSQL

### 2.1. Підключення до PostgreSQL

**Для Windows (Git Bash):**
```bash
# Підключіться як суперкористувач postgres
psql -U postgres
```

Введіть пароль, який ви встановили під час інсталяції.

**Для Linux/macOS:**
```bash
sudo -u postgres psql
```

### 2.2. Створення користувача для проєкту

Виконайте ці команди в psql:

```sql
-- Створіть користувача для проєкту
CREATE USER mmr_user WITH PASSWORD 'mmr_password';

-- Надайте права на створення баз даних
ALTER USER mmr_user CREATEDB;

-- Вийдіть з psql
\q
```

**Порада безпеки:** У продакшені використовуйте складніший пароль!

## Крок 3: Створення бази даних

### 3.1. Створіть базу даних

```bash
# Створіть базу даних mmr_db
createdb -U postgres mmr_db

# Або, якщо хочете створити від імені mmr_user:
createdb -U mmr_user mmr_db
```

**Для Windows**, якщо виникає помилка з аутентифікацією:
```bash
# Використайте явний хост
createdb -U postgres -h localhost mmr_db
```

### 3.2. Застосуйте схему бази даних

```bash
# Перейдіть до директорії проєкту
cd "D:\OneDrive\Робочий стіл\работы\Курсова 3-ий курс\код\mmr_project"

# Застосуйте схему таблиць
psql -U postgres -d mmr_db -f sql/schema.sql

# Наповніть довідник рангів
psql -U postgres -d mmr_db -f sql/seed_ranks.sql
```

### 3.3. Надайте права користувачу

```bash
# Підключіться до бази
psql -U postgres -d mmr_db
```

Виконайте в psql:

```sql
-- Надайте всі права на схему public
GRANT ALL PRIVILEGES ON DATABASE mmr_db TO mmr_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mmr_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mmr_user;

-- Надайте права на майбутні таблиці
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mmr_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mmr_user;

-- Вийдіть
\q
```

### 3.4. Перевірте створення бази

```bash
# Підключіться до бази
psql -U mmr_user -d mmr_db

# Перевірте таблиці
\dt

# Перевірте ранги
SELECT mode, name, tier, min_mmr, max_mmr FROM ranks ORDER BY mode, sort_order;

# Вийдіть
\q
```

Ви повинні побачити таблиці: `users`, `ranks`, `player_ratings`, `teams`, `team_members`, `matches`, `match_sides`, `rounds`, `rating_history`.

## Крок 4: Налаштування Python-середовища

### 4.1. Перевірте версію Python

```bash
python --version
```

Рекомендується Python 3.9 або новіший. Якщо Python не встановлений:
- Завантажте з https://www.python.org/downloads/
- Під час установки **обов'язково поставте галочку "Add Python to PATH"**

### 4.2. Створіть віртуальне середовище

```bash
# Перейдіть до директорії проєкту
cd "D:\OneDrive\Робочий стіл\работы\Курсова 3-ий курс\код\mmr_project"

# Створіть віртуальне середовище
python -m venv .venv

# Активуйте його (Git Bash на Windows)
source .venv/Scripts/activate

# Або для CMD на Windows:
# .venv\Scripts\activate.bat

# Або для PowerShell на Windows:
# .venv\Scripts\Activate.ps1
```

Після активації ви побачите `(.venv)` на початку командного рядка.

### 4.3. Встановіть залежності

```bash
# Оновіть pip
pip install --upgrade pip

# Встановіть залежності проєкту
pip install -r requirements.txt
```

## Крок 5: Налаштування підключення до БД

### 5.1. Створіть файл .env

```bash
# Скопіюйте приклад конфігурації
cp .env.example .env

# Або для Windows CMD:
# copy .env.example .env
```

### 5.2. Відредагуйте .env (якщо потрібно)

Відкрийте файл `.env` у текстовому редакторі та перевірте рядок підключення:

```env
DATABASE_URL=postgresql+psycopg2://mmr_user:mmr_password@localhost:5432/mmr_db
```

**Формат:** `postgresql+psycopg2://користувач:пароль@хост:порт/база_даних`

Якщо ви використовували інші дані (інший пароль, ім'я користувача тощо), змініть їх тут.

## Крок 6: Запуск API

### 6.1. Запустіть сервер

```bash
# Переконайтеся, що ви в директорії проєкту з активованим .venv
uvicorn app.main:app --reload
```

Ви побачите:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 6.2. Перевірте роботу API

Відкрийте браузер і перейдіть на:

- **Swagger UI (інтерактивна документація):** http://localhost:8000/docs
- **ReDoc (альтернативна документація):** http://localhost:8000/redoc

## Крок 7: Тестування API

### 7.1. Створіть тестових користувачів

Відкрийте http://localhost:8000/docs і знайдіть ендпоінт `POST /users/`.

**Користувач 1:**
```json
{
  "username": "player1",
  "email": "player1@example.com",
  "password": "password123"
}
```

**Користувач 2:**
```json
{
  "username": "player2",
  "email": "player2@example.com",
  "password": "password123"
}
```

Скопіюйте `id` створених користувачів (UUID).

### 7.2. Перевірте початковий рейтинг

Використайте ендпоінт `GET /users/{user_id}/rating/{mode}`:
- Замініть `{user_id}` на UUID користувача
- Замініть `{mode}` на `solo` або `party`

Ви повинні побачити:
```json
{
  "user_id": "...",
  "mode": "solo",
  "mmr": 1000,
  "rank": {
    "name": "Silver",
    "tier": 1
  },
  "wins": 0,
  "losses": 0,
  "matches_played": 0
}
```

### 7.3. Створіть тестовий Solo-матч

Використайте `POST /matches/solo`:
```json
{
  "user1_id": "UUID_користувача_1",
  "user2_id": "UUID_користувача_2"
}
```

Скопіюйте `match_id` зі відповіді.

### 7.4. Зіграйте раунди

Використайте `POST /matches/{match_id}/rounds`:

**Раунд 1:**
```json
{
  "coin_choice": "heads",
  "coin_result": "heads"
}
```

**Раунд 2:**
```json
{
  "coin_choice": "tails",
  "coin_result": "heads"
}
```

**Раунд 3 (вирішальний):**
```json
{
  "coin_choice": "heads",
  "coin_result": "heads"
}
```

Після завершення матчу (2 перемоги) MMR автоматично оновиться!

### 7.5. Перевірте оновлений рейтинг

Знову використайте `GET /users/{user_id}/rating/solo` для обох гравців і побачите зміни MMR.

## Крок 8: Перегляд даних у БД

### 8.1. Підключіться до бази

```bash
psql -U mmr_user -d mmr_db
```

### 8.2. Корисні SQL-запити

```sql
-- Всі користувачі
SELECT id, username, email, created_at FROM users;

-- Рейтинги гравців
SELECT u.username, pr.mode, pr.mmr, r.name, r.tier, pr.wins, pr.losses
FROM player_ratings pr
JOIN users u ON pr.user_id = u.id
LEFT JOIN ranks r ON pr.rank_id = r.id
ORDER BY pr.mode, pr.mmr DESC;

-- Історія матчів
SELECT m.id, m.mode, m.status, m.side1_mmr_snapshot, m.side2_mmr_snapshot, 
       m.winner_side, m.created_at
FROM matches m
ORDER BY m.created_at DESC;

-- Історія зміни рейтингу
SELECT u.username, rh.mode, rh.mmr_before, rh.mmr_after, rh.delta, rh.created_at
FROM rating_history rh
JOIN users u ON rh.user_id = u.id
ORDER BY rh.created_at DESC
LIMIT 10;

-- Топ-10 гравців (Solo)
SELECT u.username, pr.mmr, r.name, r.tier
FROM player_ratings pr
JOIN users u ON pr.user_id = u.id
LEFT JOIN ranks r ON pr.rank_id = r.id
WHERE pr.mode = 'solo'
ORDER BY pr.mmr DESC
LIMIT 10;

-- Вийти
\q
```

## Крок 9: Використання pgAdmin (графічний інтерфейс)

1. Запустіть **pgAdmin 4** з меню Пуск
2. Введіть майстер-пароль (якщо запитує)
3. У лівій панелі розкрийте: `Servers` → `PostgreSQL 16` → `Databases` → `mmr_db`
4. Клацніть правою кнопкою на `mmr_db` → `Query Tool`
5. Виконуйте SQL-запити у відкритому редакторі

## Усунення несправностей

### Проблема: "psql: command not found"

**Рішення:** PostgreSQL bin не додано до PATH.
- Перевірте, чи існує файл: `C:\Program Files\PostgreSQL\16\bin\psql.exe`
- Додайте цей шлях до змінної середовища PATH (див. Крок 1.10)
- Перезапустіть термінал

### Проблема: "FATAL: password authentication failed"

**Рішення:** 
- Перевірте правильність паролю
- Змініть пароль користувача:
  ```bash
  psql -U postgres
  ALTER USER mmr_user WITH PASSWORD 'новий_пароль';
  \q
  ```
- Оновіть `.env` з новим паролем

### Проблема: "could not connect to server"

**Рішення:**
- Перевірте, чи запущено PostgreSQL:
  - **Windows:** Відкрийте "Services" → знайдіть "postgresql-x64-16" → запустіть
  - **Linux/macOS:** `sudo systemctl status postgresql`
- Перевірте порт 5432: `netstat -an | grep 5432`

### Проблема: "ModuleNotFoundError: No module named 'app'"

**Рішення:**
- Переконайтеся, що ви в правильній директорії проєкту
- Активуйте віртуальне середовище: `source .venv/Scripts/activate`
- Перевстановіть залежності: `pip install -r requirements.txt`

### Проблема: "could not translate host name" на Windows

**Рішення:**
Використовуйте явний хост у командах:
```bash
psql -U postgres -h localhost -d mmr_db
createdb -U postgres -h localhost mmr_db
```

Або оновіть `.env`:
```env
DATABASE_URL=postgresql+psycopg2://mmr_user:mmr_password@127.0.0.1:5432/mmr_db
```

## Додаткові ресурси

- **Документація PostgreSQL:** https://www.postgresql.org/docs/
- **FastAPI документація:** https://fastapi.tiangolo.com/
- **SQLAlchemy документація:** https://docs.sqlalchemy.org/
- **Pydantic документація:** https://docs.pydantic.dev/

## Зупинка проєкту

```bash
# Зупиніть API сервер
# Натисніть Ctrl+C у терміналі, де запущено uvicorn

# Деактивуйте віртуальне середовище
deactivate

# Зупиніть PostgreSQL (за потреби)
# Windows: через Services або:
net stop postgresql-x64-16
```

## Наступні кроки

Після успішного запуску ви можете:

1. **Реалізувати автентифікацію:** додати JWT токени для безпеки
2. **Створити фронтенд:** React/Vue для гравців
3. **Додати матчмейкінг:** чергу підбору суперників
4. **Налаштувати міграції:** використати Alembic для версіонування БД
5. **Додати статистику:** графіки зміни MMR, історія матчів
6. **Розгорнути на сервері:** Docker + Railway/Heroku/DigitalOcean

Успіхів з вашою курсовою роботою! 🎮🏆
