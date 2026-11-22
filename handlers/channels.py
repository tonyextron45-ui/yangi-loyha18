import logging
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatJoinRequest, ChatMemberUpdated, Message

from database import Database
from keyboards.admin import admin_main_keyboard, cancel_keyboard, channel_type_keyboard
from states.states import ChannelStates

logger = logging.getLogger(__name__)
router = Router()


@router.chat_join_request()
async def on_chat_join_request(join_request: ChatJoinRequest, db: Database) -> None:
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    await db.record_join_request(chat_id, user_id)
    logger.info("Join request qayd etildi: chat_id=%s, user_id=%s", chat_id, user_id)


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated, db: Database) -> None:
    if event.chat.type not in ("channel", "supergroup"):
        return

    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    active_statuses = {"member", "administrator", "creator", "restricted"}
    inactive_statuses = {"left", "kicked"}

    if old_status not in active_statuses and new_status in active_statuses:
        await db.increment_channel_joined(event.chat.id)
    elif old_status in active_statuses and new_status in inactive_statuses:
        await db.increment_channel_left(event.chat.id)


@router.message(F.text == "📢 Kanallarni boshqarish")
async def channels_menu(message: Message, db: Database, state: FSMContext) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "📢 <b>Kanallarni boshqarish</b>\n\nKerakli amalni tanlang:",
        parse_mode="HTML",
        reply_markup=channel_type_keyboard(),
    )


@router.callback_query(F.data == "ch_list")
async def list_channels_cb(callback: CallbackQuery, db: Database) -> None:
    if not callback.from_user or not await db.is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    channels = await db.get_channels(active_only=False)
    await callback.answer()

    if not channels:
        await callback.message.answer("📭 Hozircha birorta ham kanal qo‘shilmagan.")
        return

    type_labels = {
        "mandatory": "📢 Majburiy (Oddiy)",
        "join_request": "🤝 Join Request",
        "instagram": "📸 Instagram",
        "youtube": "▶️ YouTube",
        "movie_channel": "🎬 Kino kanali",
    }
    lines = ["📋 <b>Barcha kanallar ro‘yxati:</b>\n"]
    for ch in channels:
        t_label = type_labels.get(ch["channel_type"], ch["channel_type"])
        joined = int(ch.get("joined_count", 0))
        left = int(ch.get("left_count", 0))
        lines.append(
            f"ID: <code>{ch['id']}</code> | {t_label}\n"
            f"🏷 Nomi: <b>{ch['title']}</b>\n"
            f"{joined} qo‘shildi va {left} chiqib ketdi"
        )
    await callback.message.answer("\n\n".join(lines), parse_mode="HTML")


@router.callback_query(F.data == "ch_delete")
async def delete_channel_prompt(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    if not callback.from_user or not await db.is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await callback.answer()
    await state.set_state(ChannelStates.waiting_for_delete_id)
    await callback.message.answer(
        "🗑 O‘chirmoqchi bo‘lgan kanal/sahifaning ro‘yxatdagi <b>ID</b> raqamini kiriting (masalan: <code>1</code>):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(ChannelStates.waiting_for_delete_id, F.text)
async def delete_channel_finish(message: Message, db: Database, state: FSMContext) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqamli ID kiriting:")
        return

    deleted = await db.delete_channel(int(raw))
    await state.clear()
    if deleted:
        await message.answer("✅ Ro‘yxatdan o‘chirildi.", reply_markup=admin_main_keyboard())
    else:
        await message.answer("❌ Bunday ID li yozuv topilmadi.", reply_markup=admin_main_keyboard())


@router.callback_query(F.data.startswith("ch_type:"))
async def choose_channel_type(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    if not callback.from_user or not await db.is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    ch_type = callback.data.split(":", 1)[1]
    await state.update_data(channel_type=ch_type)
    await callback.answer()

    if ch_type in ("instagram", "youtube"):
        platform_name = "Instagram" if ch_type == "instagram" else "YouTube"
        await state.set_state(ChannelStates.waiting_for_social_title)
        await callback.message.answer(
            f"<b>{platform_name}</b> sahifasi/kanali uchun o‘zingiz istagan <b>nomni</b> kiriting:",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.set_state(ChannelStates.waiting_for_channel_info)
    await callback.message.answer(
        "Kanalni ulash uchun quyidagilardan birini yuboring:\n"
        "• Kanaldan <b>biror xabarni forward qiling</b>, YOKI\n"
        "• Kanal <code>@username</code> yoki <code>-100xxxxxxxxxx</code> yuboring.\n\n"
        "<i>Eslatma: Bot ushbu kanalda administrator bo‘lishi shart!</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(ChannelStates.waiting_for_social_title, F.text)
async def save_social_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title:
        await message.answer("⚠️ Nom bo‘sh bo‘lmasligi kerak. Qayta kiriting:")
        return
    await state.update_data(social_title=title)
    await state.set_state(ChannelStates.waiting_for_social_url)
    await message.answer("🔗 Havolani (<code>https://...</code>) yuboring:", parse_mode="HTML")


@router.message(ChannelStates.waiting_for_social_url, F.text)
async def save_social_url(message: Message, db: Database, state: FSMContext) -> None:
    url = message.text.strip()
    if not (url.startswith("https://") or url.startswith("http://")):
        await message.answer("⚠️ Havola <code>https://</code> yoki <code>http://</code> bilan boshlanishi kerak. Qayta yuboring:", parse_mode="HTML")
        return

    data = await state.get_data()
    ch_type = data.get("channel_type", "instagram")
    title = data.get("social_title", "Sahifa")

    await db.add_channel(
        channel_id=0,
        title=title,
        username="",
        invite_link=url,
        channel_type=ch_type,
    )
    await state.clear()
    await message.answer(
        f"✅ <b>{title}</b> majburiy obunaga qo‘shildi!\n🔗 Havola: {url}",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


@router.message(ChannelStates.waiting_for_channel_info)
async def save_channel_info(message: Message, bot: Bot, state: FSMContext) -> None:
    chat_id: int | None = None
    username: str = ""
    invite_link: str = ""

    if message.forward_from_chat and message.forward_from_chat.type in ("channel", "supergroup"):
        chat_id = message.forward_from_chat.id
        username = message.forward_from_chat.username or ""
    elif message.text:
        raw = message.text.strip()
        try:
            if raw.startswith("@"):
                chat = await bot.get_chat(raw)
            else:
                chat = await bot.get_chat(int(raw))
            chat_id = chat.id
            username = chat.username or ""
            invite_link = chat.invite_link or ""
        except Exception as exc:
            logger.warning("Kanal ma'lumotini olishda xato (%s): %s", raw, exc)
            await message.answer(
                "❌ Kanal topilmadi yoki botda unga kirish huquqi yo‘q. "
                "Botni kanalga admin qiling va qayta urinib ko‘ring:"
            )
            return
    else:
        await message.answer("⚠️ Kanaldan xabar forward qiling yoki @username / -100ID yuboring.")
        return

    data = await state.get_data()
    ch_type = data.get("channel_type", "mandatory")

    if not invite_link and chat_id:
        try:
            creates_req = ch_type == "join_request"
            link_obj = await bot.create_chat_invite_link(
                chat_id=chat_id,
                creates_join_request=creates_req,
            )
            invite_link = link_obj.invite_link
        except Exception as exc:
            logger.warning("Taklif havolasini yaratishda xato: %s", exc)
            if username:
                invite_link = f"https://t.me/{username.lstrip('@')}"

    await state.update_data(
        pending_channel_id=chat_id,
        pending_username=username,
        pending_invite_link=invite_link,
    )
    await state.set_state(ChannelStates.waiting_for_custom_title)
    await message.answer(
        "✍️ Endi ushbu kanal uchun o‘zingiz istagan <b>nomni</b> kiriting (foydalanuvchi tugmasida shu nom ko‘rinadi):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(ChannelStates.waiting_for_custom_title, F.text)
async def save_custom_channel_title(message: Message, db: Database, state: FSMContext) -> None:
    custom_title = message.text.strip()
    if not custom_title:
        await message.answer("⚠️ Kanal nomi bo‘sh bo‘lmasligi kerak. Qayta kiriting:")
        return

    data = await state.get_data()
    chat_id = int(data["pending_channel_id"])
    username = data.get("pending_username", "")
    invite_link = data.get("pending_invite_link", "")
    ch_type = data.get("channel_type", "mandatory")

    await db.add_channel(
        channel_id=chat_id,
        title=custom_title,
        username=username,
        invite_link=invite_link,
        channel_type=ch_type,
    )
    await state.clear()
    await message.answer(
        f"✅ Kanal muvaffaqiyatli qo‘shildi!\n"
        f"🏷 Nomi: <b>{custom_title}</b>\n"
        f"🆔 ID: <code>{chat_id}</code>\n"
        f"📌 Turi: <code>{ch_type}</code>",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )
