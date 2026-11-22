import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from database import Database

logger = logging.getLogger(__name__)


async def check_mandatory_subscriptions(
    bot: Bot,
    db: Database,
    user_id: int,
    mark_social_confirmed: bool = False,
) -> tuple[bool, list[dict]]:
    enabled_raw = await db.get_setting("mandatory_sub_enabled", "1")
    if enabled_raw != "1":
        return True, []

    channels = await db.get_channels(active_only=True)
    mandatory_types = ("mandatory", "join_request", "instagram", "youtube")
    mandatory_list = [c for c in channels if c["channel_type"] in mandatory_types]

    if not mandatory_list:
        return True, []

    social_items = [c for c in mandatory_list if c["channel_type"] in ("instagram", "youtube")]
    if mark_social_confirmed and social_items:
        await db.confirm_social_list([int(s["id"]) for s in social_items], user_id)

    missing: list[dict] = []

    for ch in mandatory_list:
        ch_type = ch["channel_type"]

        if ch_type in ("instagram", "youtube"):
            confirmed = await db.has_confirmed_social(int(ch["id"]), user_id)
            if not confirmed:
                missing.append(ch)
            continue

        ch_id = int(ch["channel_id"])

        if ch_type == "join_request":
            has_req = await db.has_join_request(ch_id, user_id)
            if has_req:
                continue
            try:
                member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
                if member.status in ("creator", "administrator", "member", "restricted"):
                    continue
            except Exception:
                pass
            missing.append(ch)
        else:
            try:
                member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
                if member.status not in ("creator", "administrator", "member", "restricted"):
                    missing.append(ch)
            except (TelegramForbiddenError, TelegramBadRequest) as exc:
                logger.warning("Kanal a'zoligini tekshirishda xato (chat_id=%s): %s", ch_id, exc)
                missing.append(ch)
            except Exception as exc:
                logger.error("Kutilmagan xato (chat_id=%s): %s", ch_id, exc)
                missing.append(ch)

    return len(missing) == 0, missing


def format_movie_caption(movie: dict, include_views: bool = False) -> str:
    code = movie.get("code", "")
    title = movie.get("title", "")
    desc = (movie.get("description") or "").strip()

    lines = [
        f"🎬 <b>{title}</b>",
        f"🔢 Kino kodi: <code>{code}</code>",
    ]
    if desc:
        lines.append(f"📝 Ma'lumot: {desc}")
    if include_views:
        lines.append(f"👁 Ko‘rishlar: {movie.get('views_count', 0)}")
    return "\n".join(lines)


def format_banner_caption(movie: dict, bot_username: str) -> str:
    code = movie.get("code", "")
    title = movie.get("title", "")
    desc = (movie.get("description") or "").strip()
    clean_bot = bot_username.lstrip("@")
    link = f"https://t.me/{clean_bot}?start=movie_{code}"

    lines = [
        f"🎬 <b>{title}</b>",
        f"🔢 Kod: <code>{code}</code>",
    ]
    if desc:
        lines.append(f"📄 Tavsif: {desc}")
    lines.append(f"▶️ Tomosha qilish: <a href='{link}'>Bot orqali ochish</a>")
    return "\n".join(lines)
