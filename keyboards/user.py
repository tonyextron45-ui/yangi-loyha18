from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def user_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    if is_admin:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🛠 Admin panel")]],
            resize_keyboard=True,
        )
    return ReplyKeyboardRemove()


def subscription_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for ch in channels:
        url = (ch.get("invite_link") or "").strip()
        if not url and ch.get("username"):
            uname = str(ch["username"]).lstrip("@")
            url = f"https://t.me/{uname}"
        if url:
            ch_type = ch.get("channel_type", "mandatory")
            title = ch.get("title", "Sahifa")
            if ch_type == "instagram":
                label = f"📸 Instagram: {title}"
            elif ch_type == "youtube":
                label = f"▶️ YouTube: {title}"
            else:
                label = f"📢 Obuna bo'lish: {title}"
            buttons.append([InlineKeyboardButton(text=label, url=url)])

    buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
