from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import leaderboard, matches, teams, users

app = FastAPI(
    title="Орел/Решка — MMR & Matchmaking API",
    description="API для системи рейтингів та матчмейкінгу гравців (Solo та Party MMR).",
    version="0.1.0",
)

# Дозволяємо звернення з фронтенду (в т.ч. відкритого як локальний файл, origin "null",
# та з будь-якого localhost-порту під час розробки).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(teams.router)
app.include_router(matches.router)
app.include_router(leaderboard.router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok"}
