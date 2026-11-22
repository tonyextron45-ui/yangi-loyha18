import logging
from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards.user import subscription_keyboard, user_main_keyboard
from utils.helpers import check_mandatory_subscriptions, format_movie_caption

logger = logging.getLogger(__name__)
router = Router()


async def send_movie_to_user(message: Message, bot: Bot, db: Database, user_id: int, code: str) -> None:
    ok, missing = await check_mandatory_subscriptions(bot, db, user_id, mark_social_confirmed=False)
    if not ok:
        await message.answer(
            "🔐 Kino olish uchun avval quyidagi majburiy obunalarni bajaring:",
            reply_markup=subscription_keyboard(missing),
        )
        return

    movie = await db.get_movie_by_code(code)
    if movie:
        await db.log_movie_event(movie["id"], user_id, "search")

    if not movie:
        await message.answer("❌ Bunday kodli kino topilmadi. Kodni tekshirib qayta yuboring.")
        return

    await db.log_movie_event(movie["id"], user_id, "view")
    caption = format_movie_caption(movie, include_views=False)
    try:
        await message.answer_video(
            video=movie["file_id"],
            caption=caption,
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.error("Kino yuborishda xato (code=%s): %s", code, exc)
        await message.answer("⚠️ Kino faylini yuborishda vaqtinchalik xatolik yuz berdi.")


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, db: Database, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if not user:
        return

    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Foydalanuvchi"
    await db.upsert_user(user.id, user.username, full_name)
    is_admin = await db.is_admin(user.id)

    args = ""
    if message.text and len(message.text.split(maxsplit=1)) == 2:
        args = message.text.split(maxsplit=1)[1].strip()

    ok, missing = await check_mandatory_subscriptions(bot, db, user.id, mark_social_confirmed=False)
    if not ok:
        if args.startswith("movie_"):
            await state.update_data(pending_movie_code=args.replace("movie_", "", 1).strip())
        await message.answer(
            "🔐 Botdan to‘liq foydalanish va kinolarni ko‘rish uchun quyidagi majburiy obunalarni bajaring:",
            reply_markup=subscription_keyboard(missing),
        )
        return

    welcome_text = await db.get_setting(
        "welcome_text",
        "🎬 <b>Kino Bot</b>ga xush kelibsiz!\n\nKino kodini yuboring (masalan: <code>1025</code>).",
    )
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=user_main_keyboard(is_admin=is_admin),
    )

    if args.startswith("movie_"):
        code = args.replace("movie_", "", 1).strip()
        if code:
            await send_movie_to_user(message, bot, db, user.id, code)


@router.callback_query(F.data == "check_subscription")
async def on_check_subscription(callback: CallbackQuery, bot: Bot, db: Database, state: FSMContext) -> None:
    user = callback.from_user
    if not user:
        return

    ok, missing = await check_mandatory_subscriptions(bot, db, user.id, mark_social_confirmed=True)
    if not ok:
        await callback.answer("❗ Hali barcha majburiy kanallarga obuna bo‘lmadingiz!", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=subscription_keyboard(missing))
        except Exception:
            pass
        return

    await callback.answer("✅ Obuna tasdiqlandi!", show_alert=False)
    is_admin = await db.is_admin(user.id)
    data = await state.get_data()
    pending_code = data.get("pending_movie_code")

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "✅ Obunangiz tasdiqlandi! Endi istalgan kino kodini yuborishingiz mumkin.",
        reply_markup=user_main_keyboard(is_admin=is_admin),
    )

    if pending_code:
        await state.update_data(pending_movie_code=None)
        await send_movie_to_user(callback.message, bot, db, user.id, str(pending_code))


@router.message(F.text)
async def handle_movie_code_text(message: Message, bot: Bot, db: Database) -> None:
    user = message.from_user
    if not user or not message.text:
        return

    raw_text = message.text.strip()
    if len(raw_text) <= 25 and not raw_text.startswith("/"):
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Foydalanuvchi"
        await db.upsert_user(user.id, user.username, full_name)
        await send_movie_to_user(message, bot, db, user.id, raw_text)
