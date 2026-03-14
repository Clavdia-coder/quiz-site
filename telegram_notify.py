import httpx
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_CHAT_ID


async def notify_new_registration(game_title: str, game_date: str, location: str,
                                   team_name: str, contact_name: str,
                                   phone: str, email: str, players_count: int):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ADMIN_CHAT_ID:
        return

    text = (
        f"🎮 <b>Новая регистрация!</b>\n\n"
        f"<b>Игра:</b> {game_title}\n"
        f"<b>Дата:</b> {game_date}\n"
        f"<b>Место:</b> {location}\n\n"
        f"<b>Команда:</b> {team_name}\n"
        f"<b>Контакт:</b> {contact_name}\n"
        f"<b>Телефон:</b> {phone or '—'}\n"
        f"<b>Email:</b> {email or '—'}\n"
        f"<b>Игроков:</b> {players_count}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json={
                "chat_id": TELEGRAM_ADMIN_CHAT_ID,
                "text": text,
                "parse_mode": "HTML"
            })
        except Exception:
            pass
