# backendtest1.py
# Запуск: uvicorn backendtest1:app --reload --host 127.0.0.1 --port 800

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import aiosqlite
import os

app = FastAPI(title="SPECTER VPN API")

DB_FILE = "specter.db"

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Тарифы ────────────────────────────────────────────────────────
PLANS = {
    "forever_10": {
        "name": "10 стран (без LTE)",
        "price": 500,
        "keys_url": "https://storage.yandexcloud.net/tariff10/отобранные.txt"
    },
    "forever_15": {
        "name": "15 стран (LTE)",
        "price": 900,
        "keys_url": "https://storage.yandexcloud.net/tariff15/отобранные.txt"
    },
    "forever_20": {
        "name": "20+ стран (Много LTE)",
        "price": 1800,
        "keys_url": "https://storage.yandexcloud.net/tariff20/отобранные.txt"
    }
}

# ── Инициализация БД ──────────────────────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      TEXT PRIMARY KEY,
                plan         TEXT NOT NULL,
                plan_name    TEXT NOT NULL,
                price        INTEGER NOT NULL,
                activated_at TEXT NOT NULL,
                keys_url     TEXT NOT NULL
            )
        """)
        await db.commit()

@app.on_event("startup")
async def startup():
    await init_db()

# ── Модели ────────────────────────────────────────────────────────
class BuyRequest(BaseModel):
    user_id: str
    plan: str

# ── Роуты ─────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "SPECTER VPN API online"}


@app.get("/status/{user_id}")
async def get_status(user_id: str):
    """Статус подписки пользователя"""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return {"has_key": False, "plan": None, "activated_at": None}

    return {
        "has_key": True,
        "plan": row["plan"],
        "plan_name": row["plan_name"],
        "price": row["price"],
        "activated_at": row["activated_at"],
    }


@app.post("/buy")
async def buy(req: BuyRequest):
    """
    Активация тарифа.
    В проде сюда добавь проверку платежа (Telegram Payments / ЮKassa).
    """
    if req.plan not in PLANS:
        raise HTTPException(400, "Неизвестный тариф")

    plan = PLANS[req.plan]

    async with aiosqlite.connect(DB_FILE) as db:
        # Проверяем — уже есть подписка?
        async with db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (req.user_id,)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            raise HTTPException(409, "У пользователя уже есть активная подписка")

        activated_at = datetime.utcnow().isoformat()

        await db.execute(
            """
            INSERT INTO users (user_id, plan, plan_name, price, activated_at, keys_url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                req.user_id,
                req.plan,
                plan["name"],
                plan["price"],
                activated_at,
                plan["keys_url"],
            )
        )
        await db.commit()

    return {
        "ok": True,
        "plan": req.plan,
        "plan_name": plan["name"],
        "price": plan["price"],
        "activated_at": activated_at,
    }


@app.get("/my_keys/{user_id}")
async def my_keys(user_id: str):
    """Ссылка на файл с ключами для тарифа пользователя"""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        raise HTTPException(403, "Подписка не найдена. Сначала купите тариф.")

    return {
        "ok": True,
        "plan": row["plan"],
        "plan_name": row["plan_name"],
        "keys_url": row["keys_url"],
    }


@app.delete("/admin/reset/{user_id}")
async def admin_reset(user_id: str, secret: str = ""):
    """Сброс подписки пользователя (для тестов)"""
    if secret != "specter_admin_2026":
        raise HTTPException(403, "Forbidden")

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            existing = await cursor.fetchone()

        if not existing:
            raise HTTPException(404, "Пользователь не найден")

        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

    return {"ok": True, "message": f"Пользователь {user_id} сброшен"}


@app.get("/admin/users")
async def admin_users(secret: str = ""):
    """Список всех пользователей"""
    if secret != "specter_admin_2026":
        raise HTTPException(403, "Forbidden")

    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()

    users = [dict(row) for row in rows]
    return {"count": len(users), "users": users}
