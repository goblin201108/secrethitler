"""
Фаза Lobby: /new_game -> сбор игроков кнопкой -> /start_game (хост) ->
раздача ролей в ЛС -> переход в Nomination.
"""
import random

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from .. import db, states
from ..roles import assign_roles, build_reveal_info, build_deck

router = Router()


def lobby_keyboard(player_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Присоединиться ({player_count}/10)", callback_data="sh_join")],
        [InlineKeyboardButton(text="Начать игру", callback_data="sh_start")],
    ])


@router.message(Command("new_game"))
async def new_game(message: Message):
    existing = await db.select("games", {"chat_id": message.chat.id, "status": states.LOBBY})
    if existing:
        await message.answer("В этом чате уже собирается партия. Присоединяйся кнопкой выше 👆")
        return

    game = await db.insert("games", {
        "chat_id": message.chat.id,
        "host_id": message.from_user.id,
        "status": states.LOBBY,
    })
    await db.insert("players", {
        "game_id": game["id"],
        "user_id": message.from_user.id,
        "display_name": message.from_user.full_name,
    })

    await message.answer(
        "🎩 Собираем партию в Secret Hitler!\n"
        "Нужно от 5 до 10 игроков.\n\n"
        f"1. {message.from_user.full_name}",
        reply_markup=lobby_keyboard(1),
    )


@router.callback_query(F.data == "sh_join")
async def join_game(call: CallbackQuery):
    game = await db.select_one("games", {"chat_id": call.message.chat.id, "status": states.LOBBY})
    if not game:
        await call.answer("Лобби уже не активно.", show_alert=True)
        return

    players = await db.select("players", {"game_id": game["id"]})
    if any(p["user_id"] == call.from_user.id for p in players):
        await call.answer("Ты уже в игре.")
        return
    if len(players) >= states.MAX_PLAYERS:
        await call.answer("Уже набрано максимум игроков (10).", show_alert=True)
        return

    await db.insert("players", {
        "game_id": game["id"],
        "user_id": call.from_user.id,
        "display_name": call.from_user.full_name,
    })
    players.append({"display_name": call.from_user.full_name})

    names = "\n".join(f"{i+1}. {p['display_name']}" for i, p in enumerate(players))
    await call.message.edit_text(
        f"🎩 Собираем партию в Secret Hitler!\nНужно от 5 до 10 игроков.\n\n{names}",
        reply_markup=lobby_keyboard(len(players)),
    )
    await call.answer()


@router.callback_query(F.data == "sh_start")
async def start_game(call: CallbackQuery, bot: Bot):
    game = await db.select_one("games", {"chat_id": call.message.chat.id, "status": states.LOBBY})
    if not game:
        await call.answer("Лобби уже не активно.", show_alert=True)
        return
    if call.from_user.id != game["host_id"]:
        await call.answer("Начать игру может только тот, кто её создал.", show_alert=True)
        return

    players = await db.select("players", {"game_id": game["id"]})
    if not (states.MIN_PLAYERS <= len(players) <= states.MAX_PLAYERS):
        await call.answer(
            f"Нужно от {states.MIN_PLAYERS} до {states.MAX_PLAYERS} игроков, сейчас {len(players)}.",
            show_alert=True,
        )
        return

    player_ids = [p["user_id"] for p in players]
    roles = assign_roles(player_ids)
    reveal = build_reveal_info(roles)
    id_to_name = {p["user_id"]: p["display_name"] for p in players}

    # раздаём роли в ЛС
    for uid, role in roles.items():
        text = _role_dm_text(role, reveal[uid], id_to_name, len(players))
        try:
            await bot.send_message(uid, text)
        except Exception:
            await call.message.answer(
                f"⚠️ Не смог написать {id_to_name[uid]} в ЛС — пусть откроет чат с ботом и жмёт /start, "
                "иначе игра не сможет отправлять ему роль и карты."
            )

    # порядок хода президентов — случайная перестановка
    order = player_ids[:]
    random.shuffle(order)
    for i, uid in enumerate(order):
        await db.update("players", {"game_id": game["id"], "user_id": uid}, {
            "role": roles[uid],
            "turn_order": i,
        })

    first_president = order[0]
    await db.update("games", {"id": game["id"]}, {
        "status": states.NOMINATION,
        "player_count": len(players),
        "deck": build_deck(),
        "president_id": first_president,
    })

    await call.message.edit_text(
        f"Роли розданы в ЛС ✅\n\n"
        f"Игроков: {len(players)}\n"
        f"Первый Президент: {id_to_name[first_president]}\n\n"
        f"{id_to_name[first_president]}, выбери своего Канцлера."
    )
    await call.answer()


def _role_dm_text(role: str, info: dict, id_to_name: dict, player_count: int) -> str:
    if role == "liberal":
        return (
            "🕊 Ты — Либерал.\n\n"
            "Ты не знаешь ролей других игроков. Твоя задача — не дать фашистам "
            "принять 6 фашистских законов и не допустить, чтобы Гитлера выбрали "
            "Канцлером после 3-го фашистского закона."
        )
    if role == "fascist":
        teammates = ", ".join(id_to_name[t] for t in info["teammates"] if t != info["hitler_id"])
        hitler_name = id_to_name[info["hitler_id"]]
        extra = f"Другие фашисты: {teammates}\n" if teammates else ""
        return (
            "🔴 Ты — Фашист.\n\n"
            f"{extra}Гитлер: {hitler_name}\n\n"
            "Помогай Гитлеру попасть в Канцлеры и проводи фашистские законы, "
            "но не спали свою роль раньше времени."
        )
    if role == "hitler":
        if info["knows_fascists"]:
            teammates = ", ".join(id_to_name[t] for t in info["teammates"])
            return (
                "💀 Ты — Гитлер.\n\n"
                f"Игроков {player_count} (5-6), поэтому ты знаешь своего фашиста: {teammates}\n\n"
                "Веди себя как либерал на публике. Если тебя выберут Канцлером "
                "после 3-го фашистского закона — фашисты побеждают мгновенно."
            )
        return (
            "💀 Ты — Гитлер.\n\n"
            f"Игроков {player_count} (7+), поэтому даже ты не знаешь, кто фашисты — "
            "придётся действовать вслепую и ждать сигналов от своей команды.\n\n"
            "Веди себя как либерал на публике. Если тебя выберут Канцлером "
            "после 3-го фашистского закона — фашисты побеждают мгновенно."
        )
    raise ValueError(role)
