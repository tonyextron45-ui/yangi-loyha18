import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards.admin import admin_main_keyboard, bot_settings_keyboard, cancel_keyboard
from keyboards.user import user_main_keyboard
from states.states import BotSettingsStates

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("admin"))
@router.message(F.text == "🛠 Admin panel")
async def open_admin_panel(message: Message, db: Database, state: FSMContext) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🛠 <b>Admin Boshqaruv Paneli</b>\n\nKerakli bo‘limni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


@router.message(F.text == "⬅️ Foydalanuvchi menyusi")
async def back_to_user_menu(message: Message, db: Database, state: FSMContext) -> None:
    if not message.from_user:
        return
    await state.clear()
    is_admin = await db.is_admin(message.from_user.id)
    await message.answer(
        "🏠 Foydalanuvchi menyusiga qaytdingiz.",
        reply_markup=user_main_keyboard(is_admin=is_admin),
    )


@router.message(F.text == "📊 Statistika")
async def admin_stats_handler(message: Message, db: Database) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return

    stats = await db.get_stats()

    searched_lines = []
    for i, item in enumerate(stats["top_searched"], start=1):
        searched_lines.append(f"{i}. {item['title']} (<code>{item['code']}</code>) — {item['search_count']} marta")

    viewed_lines = []
    for i, item in enumerate(stats["top_viewed"], start=1):
        viewed_lines.append(f"{i}. {item['title']} (<code>{item['code']}</code>) — {item['views_count']} marta")

    text = (
        "📊 <b>Batafsil Admin Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🆕 Bugungi foydalanuvchilar: <b>{stats['today_users']}</b>\n"
        f"🎬 Jami kinolar: <b>{stats['total_movies']}</b>\n"
        f"🔍 Jami kino so‘rovlari: <b>{stats['total_searches']}</b>\n"
        f"▶️ Jami yuborilgan kinolar: <b>{stats['total_views']}</b>\n\n"
        "🔎 <b>Eng ko‘p qidirilgan kinolar:</b>\n"
        + ("\n".join(searched_lines) if searched_lines else "Ma'lumot yo‘q")
        + "\n\n"
        "🏆 <b>Eng ko‘p yuborilgan kinolar:</b>\n"
        + ("\n".join(viewed_lines) if viewed_lines else "Ma'lumot yo‘q")
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🔐 Majburiy obuna sozlamalari")
async def mandatory_sub_settings(message: Message, db: Database) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return
    sub_enabled = (await db.get_setting("mandatory_sub_enabled", "1")) == "1"
    banner_enabled = (await db.get_setting("banner_enabled", "1")) == "1"
    await message.answer(
        "🔐 <b>Majburiy obuna va bot sozlamalari:</b>",
        parse_mode="HTML",
        reply_markup=bot_settings_keyboard(sub_enabled, banner_enabled),
    )


@router.message(F.text == "🖼 Banner sozlamalari")
async def banner_settings_handler(message: Message, db: Database) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return
    sub_enabled = (await db.get_setting("mandatory_sub_enabled", "1")) == "1"
    banner_enabled = (await db.get_setting("banner_enabled", "1")) == "1"
    movie_chs = await db.get_channels(channel_type="movie_channel", active_only=True)
    ch_names = ", ".join(c["title"] for c in movie_chs) if movie_chs else "Ulanmagan"

    await message.answer(
        f"🖼 <b>Banner Sozlamalari</b>\n"
        f"Holati: <b>{'Yoqilgan ✅' if banner_enabled else 'O‘chirilgan ❌'}</b>\n"
        f"Kino kanallari: <b>{ch_names}</b>",
        parse_mode="HTML",
        reply_markup=bot_settings_keyboard(sub_enabled, banner_enabled),
    )


@router.message(F.text == "⚙️ Bot sozlamalari")
async def bot_settings_handler(message: Message, db: Database) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return
    sub_enabled = (await db.get_setting("mandatory_sub_enabled", "1")) == "1"
    banner_enabled = (await db.get_setting("banner_enabled", "1")) == "1"
    admins = await db.get_admins()
    admin_ids_str = ", ".join(f"<code>{a['user_id']}</code>" for a in admins)

    await message.answer(
        f"⚙️ <b>Bot Sozlamalari</b>\n"
        f"Adminlar: {admin_ids_str}",
        parse_mode="HTML",
        reply_markup=bot_settings_keyboard(sub_enabled, banner_enabled),
    )


@router.callback_query(F.data == "toggle_sub")
async def toggle_mandatory_sub(callback: CallbackQuery, db: Database) -> None:
    if not callback.from_user or not await db.is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    current = (await db.get_setting("mandatory_sub_enabled", "1")) == "1"
    new_val = "0" if current else "1"
    await db.set_setting("mandatory_sub_enabled", new_val)

    banner_enabled = (await db.get_setting("banner_enabled", "1")) == "1"
    await callback.answer("Holat o‘zgartirildi")
    await callback.message.edit_reply_markup(
        reply_markup=bot_settings_keyboard(new_val == "1", banner_enabled)
    )


@router.callback_query(F.data == "toggle_banner")
async def toggle_banner_sending(callback: CallbackQuery, db: Database) -> None:
    if not callback.from_user or not await db.is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    current = (await db.get_setting("banner_enabled", "1")) == "1"
    new_val = "0" if current else "1"
    await db.set_setting("banner_enabled", new_val)

    sub_enabled = (await db.get_setting("mandatory_sub_enabled", "1")) == "1"
    await callback.answer("Banner holati yangilandi")
    await callback.message.edit_reply_markup(
        reply_markup=bot_settings_keyboard(sub_enabled, new_val == "1")
    )


@router.callback_query(F.data == "set_welcome")
async def set_welcome_prompt(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    if not callback.from_user or not await db.is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await callback.answer()
    await state.set_state(BotSettingsStates.waiting_for_welcome_text)
    await callback.message.answer(
        "✍️ Yangi salomlashish matnini yuboring (HTML teglar qo‘llab-quvvatlanadi):",
        reply_markup=cancel_keyboard(),
    )


@router.message(BotSettingsStates.waiting_for_welcome_text, F.text)
async def set_welcome_save(message: Message, db: Database, state: FSMContext) -> None:
    await db.set_setting("welcome_text", message.text.strip())
    await state.clear()
    await message.answer("✅ Salomlashish matni saqlandi.", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "add_admin")
async def add_admin_prompt(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    if not callback.from_user or not await db.is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await callback.answer()
    await state.set_state(BotSettingsStates.waiting_for_new_admin_id)
    await callback.message.answer(
        "👤 Yangi administratorning Telegram <b>ID</b> raqamini kiriting:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(BotSettingsStates.waiting_for_new_admin_id, F.text)
async def add_admin_save(message: Message, db: Database, state: FSMContext) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer("⚠️ Faqat raqamli Telegram ID kiriting:")
        return
    new_admin_id = int(raw)
    added_by = message.from_user.id if message.from_user else new_admin_id
    await db.add_admin(new_admin_id, added_by)
    await state.clear()
    await message.answer(
        f"✅ <code>{new_admin_id}</code> adminlar ro‘yxatiga qo‘shildi.",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


@router.callback_query(F.data == "remove_admin")
async def remove_admin_prompt(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    if not callback.from_user or not await db.is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await callback.answer()
    await state.set_state(BotSettingsStates.waiting_for_remove_admin_id)
    await callback.message.answer(
        "🗑 O‘chiriladigan administratorning Telegram <b>ID</b> raqamini kiriting:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(BotSettingsStates.waiting_for_remove_admin_id, F.text)
async def remove_admin_save(message: Message, db: Database, state: FSMContext) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer("⚠️ Faqat raqamli Telegram ID kiriting:")
        return
    removed = await db.remove_admin(int(raw))
    await state.clear()
    if removed:
        await message.answer("✅ Admin o‘chirildi.", reply_markup=admin_main_keyboard())
    else:
        await message.answer("❌ Admin o‘chirilmadi (balki u .env dagi asosiy admin yoki mavjud emas).", reply_markup=admin_main_keyboard())
