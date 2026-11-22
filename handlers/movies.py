import logging
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards.admin import (
    admin_main_keyboard,
    cancel_keyboard,
    edit_movie_actions_keyboard,
    skip_or_cancel_keyboard,
)
from states.states import AddMovieStates, DeleteMovieStates, EditMovieStates
from utils.helpers import format_banner_caption, format_movie_caption

logger = logging.getLogger(__name__)
router = Router()


async def _publish_banner_if_enabled(bot: Bot, db: Database, movie: dict) -> None:
    banner_enabled = await db.get_setting("banner_enabled", "1")
    if banner_enabled != "1":
        return

    banner_id = (movie.get("banner_file_id") or "").strip()
    if not banner_id:
        return

    movie_channels = await db.get_channels(channel_type="movie_channel", active_only=True)
    if not movie_channels:
        return

    bot_info = await bot.get_me()
    caption = format_banner_caption(movie, bot_info.username or "")

    for ch in movie_channels:
        try:
            await bot.send_photo(
                chat_id=int(ch["channel_id"]),
                photo=banner_id,
                caption=caption,
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.error("Banner yuborishda xato (channel_id=%s): %s", ch["channel_id"], exc)


@router.message(F.text == "❌ Bekor qilish")
async def cancel_any_state(message: Message, db: Database, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id if message.from_user else 0
    if await db.is_admin(user_id):
        await message.answer("Amal bekor qilindi.", reply_markup=admin_main_keyboard())
    else:
        await message.answer("Amal bekor qilindi.")


@router.message(F.text == "➕ Kino qo‘shish")
async def start_add_movie(message: Message, db: Database, state: FSMContext) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(AddMovieStates.waiting_for_video)
    await message.answer(
        "1/5 bosqich: Kino <b>videosini</b> yuboring.",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddMovieStates.waiting_for_video, F.video)
async def add_movie_video(message: Message, state: FSMContext) -> None:
    video = message.video
    await state.update_data(file_id=video.file_id)
    await state.set_state(AddMovieStates.waiting_for_title)
    await message.answer("2/5 bosqich: Kino <b>nomini</b> kiriting:", parse_mode="HTML", reply_markup=cancel_keyboard())


@router.message(AddMovieStates.waiting_for_video)
async def add_movie_video_invalid(message: Message) -> None:
    await message.answer("⚠️ Iltimos, faqat video fayl yuboring yoki «❌ Bekor qilish» tugmasini bosing.")


@router.message(AddMovieStates.waiting_for_title, F.text)
async def add_movie_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title:
        await message.answer("⚠️ Kino nomi bo‘sh bo‘lmasligi kerak. Qayta kiriting:")
        return
    await state.update_data(title=title)
    await state.set_state(AddMovieStates.waiting_for_code)
    await message.answer("3/5 bosqich: Kino <b>kodini</b> kiriting (masalan: <code>1025</code>):", parse_mode="HTML")


@router.message(AddMovieStates.waiting_for_code, F.text)
async def add_movie_code(message: Message, db: Database, state: FSMContext) -> None:
    code = message.text.strip()
    if not code:
        await message.answer("⚠️ Kino kodi bo‘sh bo‘lmasligi kerak. Qayta kiriting:")
        return

    existing = await db.get_movie_by_code(code)
    if existing:
        await message.answer(
            f"❌ <b>{code}</b> kodli kino allaqachon mavjud (<i>{existing['title']}</i>).\n"
            "Boshqa noyob kod kiriting:",
            parse_mode="HTML",
        )
        return

    await state.update_data(code=code)
    await state.set_state(AddMovieStates.waiting_for_description)
    await message.answer(
        "4/5 bosqich: Kino haqida <b>ma'lumot</b> kiriting (ixtiyoriy):",
        parse_mode="HTML",
        reply_markup=skip_or_cancel_keyboard(),
    )


@router.message(AddMovieStates.waiting_for_description, F.text)
async def add_movie_description(message: Message, state: FSMContext) -> None:
    desc = "" if message.text == "⏭ O‘tkazib yuborish" else message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(AddMovieStates.waiting_for_banner)
    await message.answer(
        "5/5 bosqich: Kino <b>banner rasmini</b> yuboring (ixtiyoriy):",
        parse_mode="HTML",
        reply_markup=skip_or_cancel_keyboard(),
    )


@router.message(AddMovieStates.waiting_for_banner, F.photo)
async def add_movie_banner_photo(message: Message, bot: Bot, db: Database, state: FSMContext) -> None:
    banner_file_id = message.photo[-1].file_id
    await _finalize_add_movie(message, bot, db, state, banner_file_id)


@router.message(AddMovieStates.waiting_for_banner, F.text == "⏭ O‘tkazib yuborish")
async def add_movie_banner_skip(message: Message, bot: Bot, db: Database, state: FSMContext) -> None:
    await _finalize_add_movie(message, bot, db, state, "")


@router.message(AddMovieStates.waiting_for_banner)
async def add_movie_banner_invalid(message: Message) -> None:
    await message.answer("⚠️ Rasm yuboring yoki «⏭ O‘tkazib yuborish» tugmasini bosing.")


async def _finalize_add_movie(
    message: Message,
    bot: Bot,
    db: Database,
    state: FSMContext,
    banner_file_id: str,
) -> None:
    data = await state.get_data()
    ok, movie_id = await db.add_movie(
        code=data["code"],
        title=data["title"],
        description=data.get("description", ""),
        file_id=data["file_id"],
        banner_file_id=banner_file_id,
    )
    await state.clear()

    if not ok or movie_id is None:
        await message.answer(
            "❌ Xatolik: Ushbu kino kodi bazada allaqachon mavjud.",
            reply_markup=admin_main_keyboard(),
        )
        return

    movie = await db.get_movie_by_id(movie_id)
    if movie:
        await _publish_banner_if_enabled(bot, db, movie)

    await message.answer(
        f"✅ Kino muvaffaqiyatli qo‘shildi!\n"
        f"🎬 Nomi: <b>{data['title']}</b>\n"
        f"🔢 Kodi: <code>{data['code']}</code>",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


@router.message(F.text == "📚 Kinolar ro‘yxati")
async def list_movies_cmd(message: Message, db: Database) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return

    total = await db.count_movies()
    movies = await db.list_movies(limit=25, offset=0)
    if not movies:
        await message.answer("📭 Bazada hozircha kinolar mavjud emas.")
        return

    lines = [f"📚 <b>Kinolar ro‘yxati</b> (Jami: {total} ta, oxirgi {len(movies)} tasi):\n"]
    for idx, m in enumerate(movies, start=1):
        lines.append(
            f"{idx}. <b>{m['title']}</b> | Kod: <code>{m['code']}</code> | 👁 {m['views_count']} | 🔍 {m['search_count']}"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "🗑 Kino o‘chirish")
async def delete_movie_start(message: Message, db: Database, state: FSMContext) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(DeleteMovieStates.waiting_for_code)
    await message.answer(
        "🗑 O‘chirmoqchi bo‘lgan kino <b>kodini</b> kiriting:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(DeleteMovieStates.waiting_for_code, F.text)
async def delete_movie_finish(message: Message, db: Database, state: FSMContext) -> None:
    code = message.text.strip()
    deleted = await db.delete_movie_by_code(code)
    await state.clear()

    if deleted:
        await message.answer(
            f"✅ <code>{code}</code> kodli kino bazadan o‘chirildi.",
            parse_mode="HTML",
            reply_markup=admin_main_keyboard(),
        )
    else:
        await message.answer(
            f"❌ <code>{code}</code> kodli kino topilmadi.",
            parse_mode="HTML",
            reply_markup=admin_main_keyboard(),
        )


@router.message(F.text == "✏️ Kino tahrirlash")
async def edit_movie_start(message: Message, db: Database, state: FSMContext) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(EditMovieStates.waiting_for_code_search)
    await message.answer(
        "✏️ Tahrirlamoqchi bo‘lgan kino <b>kodini</b> kiriting:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(EditMovieStates.waiting_for_code_search, F.text)
async def edit_movie_find(message: Message, db: Database, state: FSMContext) -> None:
    code = message.text.strip()
    movie = await db.get_movie_by_code(code)
    if not movie:
        await message.answer("❌ Bunday kodli kino topilmadi. Qayta kod kiriting:")
        return

    await state.update_data(edit_movie_id=movie["id"])
    await state.set_state(EditMovieStates.choosing_action)
    await message.answer("Kino topildi. Tahrirlash menyusi:", reply_markup=admin_main_keyboard())
    await message.answer(
        format_movie_caption(movie, include_views=True),
        parse_mode="HTML",
        reply_markup=edit_movie_actions_keyboard(int(movie["id"])),
    )


@router.callback_query(F.data == "edit_close")
async def edit_movie_close(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Yopildi")
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("edit_title:"))
async def edit_title_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    await state.update_data(edit_movie_id=movie_id)
    await state.set_state(EditMovieStates.waiting_for_new_title)
    await callback.answer()
    await callback.message.answer("📝 Yangi kino <b>nomini</b> kiriting:", parse_mode="HTML", reply_markup=cancel_keyboard())


@router.message(EditMovieStates.waiting_for_new_title, F.text)
async def edit_title_save(message: Message, db: Database, state: FSMContext) -> None:
    data = await state.get_data()
    movie_id = int(data["edit_movie_id"])
    ok, msg = await db.update_movie_field(movie_id, "title", message.text)
    await state.clear()
    await message.answer(f"{'✅' if ok else '❌'} {msg}", reply_markup=admin_main_keyboard())


@router.callback_query(F.data.startswith("edit_code:"))
async def edit_code_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    await state.update_data(edit_movie_id=movie_id)
    await state.set_state(EditMovieStates.waiting_for_new_code)
    await callback.answer()
    await callback.message.answer("🔢 Yangi kino <b>kodini</b> kiriting:", parse_mode="HTML", reply_markup=cancel_keyboard())


@router.message(EditMovieStates.waiting_for_new_code, F.text)
async def edit_code_save(message: Message, db: Database, state: FSMContext) -> None:
    data = await state.get_data()
    movie_id = int(data["edit_movie_id"])
    ok, msg = await db.update_movie_field(movie_id, "code", message.text)
    await state.clear()
    await message.answer(f"{'✅' if ok else '❌'} {msg}", reply_markup=admin_main_keyboard())


@router.callback_query(F.data.startswith("edit_video:"))
async def edit_video_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    await state.update_data(edit_movie_id=movie_id)
    await state.set_state(EditMovieStates.waiting_for_new_video)
    await callback.answer()
    await callback.message.answer("🎞 Yangi kino <b>videosini</b> yuboring:", parse_mode="HTML", reply_markup=cancel_keyboard())


@router.message(EditMovieStates.waiting_for_new_video, F.video)
async def edit_video_save(message: Message, db: Database, state: FSMContext) -> None:
    data = await state.get_data()
    movie_id = int(data["edit_movie_id"])
    ok, msg = await db.update_movie_field(movie_id, "file_id", message.video.file_id)
    await state.clear()
    await message.answer(f"{'✅' if ok else '❌'} {msg}", reply_markup=admin_main_keyboard())


@router.callback_query(F.data.startswith("edit_banner:"))
async def edit_banner_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    await state.update_data(edit_movie_id=movie_id)
    await state.set_state(EditMovieStates.waiting_for_new_banner)
    await callback.answer()
    await callback.message.answer("🖼 Yangi <b>banner rasmini</b> yuboring:", parse_mode="HTML", reply_markup=cancel_keyboard())


@router.message(EditMovieStates.waiting_for_new_banner, F.photo)
async def edit_banner_save(message: Message, db: Database, state: FSMContext) -> None:
    data = await state.get_data()
    movie_id = int(data["edit_movie_id"])
    ok, msg = await db.update_movie_field(movie_id, "banner_file_id", message.photo[-1].file_id)
    await state.clear()
    await message.answer(f"{'✅' if ok else '❌'} {msg}", reply_markup=admin_main_keyboard())
