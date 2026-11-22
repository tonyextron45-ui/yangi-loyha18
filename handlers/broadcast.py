import asyncio
import logging
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards.admin import admin_main_keyboard, broadcast_confirm_keyboard, cancel_keyboard
from states.states import BroadcastStates

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "📨 Foydalanuvchilarga xabar yuborish")
async def start_broadcast(message: Message, db: Database, state: FSMContext) -> None:
    if not message.from_user or not await db.is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(BroadcastStates.waiting_for_content)
    await message.answer(
        "📨 Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:\n"
        "• Matn\n• Rasm\n• Video\n• Forward qilingan xabar",
        reply_markup=cancel_keyboard(),
    )


@router.message(BroadcastStates.waiting_for_content)
async def preview_broadcast(message: Message, state: FSMContext) -> None:
    await state.update_data(
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
    )
    await state.set_state(BroadcastStates.waiting_for_confirm)
    await message.answer(
        "👆 Yuqoridagi xabar barcha foydalanuvchilarga yuborilsinmi?",
        reply_markup=broadcast_confirm_keyboard(),
    )


@router.callback_query(BroadcastStates.waiting_for_confirm, F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Bekor qilindi")
    await callback.message.answer("❌ Xabar yuborish bekor qilindi.", reply_markup=admin_main_keyboard())


@router.callback_query(BroadcastStates.waiting_for_confirm, F.data == "broadcast_confirm")
async def execute_broadcast(callback: CallbackQuery, bot: Bot, db: Database, state: FSMContext) -> None:
    data = await state.get_data()
    source_chat_id = data.get("source_chat_id")
    source_message_id = data.get("source_message_id")
    await state.clear()
    await callback.answer("Xabar yuborish boshlandi...")

    user_ids = await db.get_all_user_ids()
    sent_count = 0
    error_count = 0

    status_msg = await callback.message.answer(f"⏳ Yuborilmoqda... (0 / {len(user_ids)})")

    for idx, uid in enumerate(user_ids, start=1):
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=source_chat_id,
                message_id=source_message_id,
            )
            sent_count += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after + 1)
            try:
                await bot.copy_message(
                    chat_id=uid,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                )
                sent_count += 1
            except Exception:
                error_count += 1
        except TelegramForbiddenError:
            error_count += 1
        except Exception as exc:
            logger.warning("Broadcast xatosi (user_id=%s): %s", uid, exc)
            error_count += 1

        if idx % 25 == 0:
            await asyncio.sleep(0.05)

    try:
        await status_msg.delete()
    except Exception:
        pass

    await callback.message.answer(
        "✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"📨 Yuborildi: <b>{sent_count}</b> ta\n"
        f"⚠️ Xatoliklar (bloklagan/topilmagan): <b>{error_count}</b> ta",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )
