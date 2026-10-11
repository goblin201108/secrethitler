"""
Тонкая обёртка над Supabase REST (PostgREST) через aiohttp напрямую —
без supabase-py, тем же паттерном, что уже используется в Чожуке.
"""
import os
import aiohttp

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


async def _request(method: str, table: str, *, params=None, json=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=HEADERS, params=params, json=json) as resp:
            resp.raise_for_status()
            if resp.content_length == 0:
                return None
            return await resp.json()


async def insert(table: str, row: dict) -> dict:
    result = await _request("POST", table, json=row)
    return result[0]


async def insert_many(table: str, rows: list[dict]) -> list[dict]:
    return await _request("POST", table, json=rows)


async def update(table: str, match: dict, values: dict) -> list[dict]:
    params = {f"{k}": f"eq.{v}" for k, v in match.items()}
    return await _request("PATCH", table, params=params, json=values)


async def select(table: str, match: dict | None = None, columns: str = "*") -> list[dict]:
    params = {"select": columns}
    if match:
        params.update({k: f"eq.{v}" for k, v in match.items()})
    return await _request("GET", table, params=params)


async def select_one(table: str, match: dict, columns: str = "*") -> dict | None:
    rows = await select(table, match, columns)
    return rows[0] if rows else None
