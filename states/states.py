from aiogram.fsm.state import State, StatesGroup


class AddMovieStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_title = State()
    waiting_for_code = State()
    waiting_for_description = State()
    waiting_for_banner = State()


class EditMovieStates(StatesGroup):
    waiting_for_code_search = State()
    choosing_action = State()
    waiting_for_new_title = State()
    waiting_for_new_code = State()
    waiting_for_new_video = State()
    waiting_for_new_banner = State()


class DeleteMovieStates(StatesGroup):
    waiting_for_code = State()


class ChannelStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_channel_info = State()
    waiting_for_custom_title = State()
    waiting_for_social_title = State()
    waiting_for_social_url = State()
    waiting_for_delete_id = State()


class BroadcastStates(StatesGroup):
    waiting_for_content = State()
    waiting_for_confirm = State()


class BotSettingsStates(StatesGroup):
    waiting_for_welcome_text = State()
    waiting_for_new_admin_id = State()
    waiting_for_remove_admin_id = State()
