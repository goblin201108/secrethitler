"""
Состояния партии. Хранятся как обычная строка в games.status —
никакой отдельной FSM-библиотеки не нужно, весь стейт живёт в Supabase,
что и позволяет боту оставаться stateless между вызовами на Vercel.
"""

LOBBY = "lobby"
NOMINATION = "nomination"
VOTING = "voting"
LEGISLATIVE_PRESIDENT = "legislative_president"
LEGISLATIVE_CHANCELLOR = "legislative_chancellor"
EXECUTIVE_ACTION = "executive_action"
GAME_OVER = "game_over"

MIN_PLAYERS = 5
MAX_PLAYERS = 10
