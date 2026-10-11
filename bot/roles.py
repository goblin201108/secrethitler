"""
Распределение ролей по количеству игроков + логика раскрытия
информации фашистам/Гитлеру в ЛС при старте партии.

Официальная таблица распределения (либералы / фашисты без Гитлера / Гитлер):
"""
import random

ROLE_DISTRIBUTION = {
    5:  {"liberal": 3, "fascist": 1, "hitler": 1},
    6:  {"liberal": 4, "fascist": 1, "hitler": 1},
    7:  {"liberal": 4, "fascist": 2, "hitler": 1},
    8:  {"liberal": 5, "fascist": 2, "hitler": 1},
    9:  {"liberal": 5, "fascist": 3, "hitler": 1},
    10: {"liberal": 6, "fascist": 3, "hitler": 1},
}

# Силы президента по клеткам фашистского трека (индекс 0 = после 1-го закона).
# None = сила не открывается.
EXECUTIVE_POWERS = {
    5:  [None, None, "peek",       "execution", "execution", None],
    6:  [None, None, "peek",       "execution", "execution", None],
    7:  [None, "investigate", "special_election", "execution", "execution", None],
    8:  [None, "investigate", "special_election", "execution", "execution", None],
    9:  ["investigate", "investigate", "special_election", "execution", "execution", None],
    10: ["investigate", "investigate", "special_election", "execution", "execution", None],
}

DECK_LIBERAL = 6
DECK_FASCIST = 11


def build_deck() -> list[str]:
    """Полная колода 6 либеральных + 11 фашистских карт, перемешанная."""
    deck = ["L"] * DECK_LIBERAL + ["F"] * DECK_FASCIST
    random.shuffle(deck)
    return deck


def assign_roles(player_ids: list[int]) -> dict[int, str]:
    """
    player_ids — список telegram user_id в произвольном порядке.
    Возвращает {user_id: "liberal" | "fascist" | "hitler"}.
    """
    n = len(player_ids)
    if n not in ROLE_DISTRIBUTION:
        raise ValueError(f"Secret Hitler поддерживает 5-10 игроков, получено {n}")

    dist = ROLE_DISTRIBUTION[n]
    pool = (
        ["liberal"] * dist["liberal"]
        + ["fascist"] * dist["fascist"]
        + ["hitler"] * dist["hitler"]
    )
    random.shuffle(pool)
    return dict(zip(player_ids, pool))


def build_reveal_info(roles: dict[int, str]) -> dict[int, dict]:
    """
    Для каждого игрока формирует, что именно ему показать в ЛС при раздаче.

    Правила раскрытия:
    - Фашисты (не Гитлер) знают друг друга и знают, кто Гитлер, всегда.
    - Гитлер знает фашистов, только если игроков <= 6 (мало игроков — нужна
      более тесная координация). При 7+ игроках Гитлер их не знает.
    - Либералы не знают ничьих ролей.
    """
    n = len(roles)
    hitler_id = next(uid for uid, r in roles.items() if r == "hitler")
    fascist_ids = [uid for uid, r in roles.items() if r == "fascist"]

    info: dict[int, dict] = {}
    for uid, role in roles.items():
        if role == "liberal":
            info[uid] = {"role": "liberal", "teammates": []}
        elif role == "fascist":
            teammates = [f for f in fascist_ids if f != uid] + [hitler_id]
            info[uid] = {"role": "fascist", "teammates": teammates, "hitler_id": hitler_id}
        elif role == "hitler":
            if n <= 6:
                info[uid] = {"role": "hitler", "teammates": fascist_ids, "knows_fascists": True}
            else:
                info[uid] = {"role": "hitler", "teammates": [], "knows_fascists": False}
    return info


def get_power_for_slot(player_count: int, fascist_policies_enacted: int) -> str | None:
    """Какая сила открывается за только что принятый N-й фашистский закон (1-индексация)."""
    powers = EXECUTIVE_POWERS[player_count]
    idx = fascist_policies_enacted - 1
    if 0 <= idx < len(powers):
        return powers[idx]
    return None
