from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def admin_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="➕ Kino qo‘shish"), KeyboardButton(text="📚 Kinolar ro‘yxati")],
        [KeyboardButton(text="🗑 Kino o‘chirish"), KeyboardButton(text="✏️ Kino tahrirlash")],
        [KeyboardButton(text="📢 Kanallarni boshqarish"), KeyboardButton(text="🔐 Majburiy obuna sozlamalari")],
        [KeyboardButton(text="🖼 Banner sozlamalari"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📨 Foydalanuvchilarga xabar yuborish"), KeyboardButton(text="⚙️ Bot sozlamalari")],
        [KeyboardButton(text="⬅️ Foydalanuvchi menyusi")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def skip_or_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ O‘tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
    )


def edit_movie_actions_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Nomini o‘zgartirish", callback_data=f"edit_title:{movie_id}"),
                InlineKeyboardButton(text="🔢 Kodini o‘zgartirish", callback_data=f"edit_code:{movie_id}"),
            ],
            [
                InlineKeyboardButton(text="🎞 Faylni almashtirish", callback_data=f"edit_video:{movie_id}"),
                InlineKeyboardButton(text="🖼 Bannerni almashtirish", callback_data=f"edit_banner:{movie_id}"),
            ],
            [
                InlineKeyboardButton(text="❌ Yopish", callback_data="edit_close"),
            ],
        ]
    )


def channel_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Majburiy kanal (Oddiy)", callback_data="ch_type:mandatory")],
            [InlineKeyboardButton(text="🤝 Join Request kanali", callback_data="ch_type:join_request")],
            [InlineKeyboardButton(text="📸 Instagram qo‘shish", callback_data="ch_type:instagram")],
            [InlineKeyboardButton(text="▶️ YouTube qo‘shish", callback_data="ch_type:youtube")],
            [InlineKeyboardButton(text="🎬 Kino kanali (Banner uchun)", callback_data="ch_type:movie_channel")],
            [InlineKeyboardButton(text="📋 Barcha kanallar ro‘yxati", callback_data="ch_list")],
            [InlineKeyboardButton(text="🗑 Kanal o‘chirish", callback_data="ch_delete")],
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yuborishni tasdiqlash", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel"),
            ]
        ]
    )


def bot_settings_keyboard(sub_enabled: bool, banner_enabled: bool) -> InlineKeyboardMarkup:
    sub_label = "🔐 Majburiy obuna: YOQILGAN ✅" if sub_enabled else "🔐 Majburiy obuna: O‘CHIRILGAN ❌"
    ban_label = "🖼 Banner yuborish: YOQILGAN ✅" if banner_enabled else "🖼 Banner yuborish: O‘CHIRILGAN ❌"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=sub_label, callback_data="toggle_sub")],
            [InlineKeyboardButton(text=ban_label, callback_data="toggle_banner")],
            [InlineKeyboardButton(text="✍️ Salomlashish matni", callback_data="set_welcome")],
            [InlineKeyboardButton(text="👤 Admin qo‘shish", callback_data="add_admin")],
            [InlineKeyboardButton(text="🗑 Admin o‘chirish", callback_data="remove_admin")],
        ]
    )
