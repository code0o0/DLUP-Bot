from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.enums import ChatType
from html import escape

from bot import bot, user_data, OWNER_ID
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import new_task


@new_task
async def info(client, message):
    msg = ''
    user = message.from_user or message.sender_chat
    user_id = user.id
    text = message.text.split()[1] if len(message.text.split()) > 1 else None
    if user_id in user_data and user_data[user_id].get('is_sudo'):
        is_sudo = True
    elif user_id == OWNER_ID:
        is_sudo = True
    else:
        is_sudo = False
    if all([text, is_sudo]):
        if text.isdigit():
            queried_id = int(text)
        else:
            text = text.strip('https://t.me/')
            queried_id = text if text.startswith('@') else f'@{text}'
        try:
            user = await bot.get_users(queried_id)
            username = user.username or user.mention
            userid = user.id
            dc_id = user.dc_id
            msg += "<b>User Information</b>\n"
            msg += f'<b>User: </b>@{escape(username)}\n'
            msg += f'<b>User-ID: </b><code>{userid}</code>\n'
            msg += f'<b>DC-ID: </b><code>{dc_id}</code>\n\n'
        except Exception as e:
            msg += f'<b>User not found!</b>\n'
        try:
            chat = await bot.get_chat(queried_id)
            chat_title = chat.title
            chat_id = chat.id
            chat_name = chat.username or "Unknown"
            dc_id = chat.dc_id
            distance = chat.distance
            msg += "<b>Chat Information</b>\n"
            msg += f'<b>Chat-Title: </b>{escape(chat_title)}\n'
            msg += f'<b>Chat-ID: </b><code>{chat_id}</code>\n'
            msg += f'<b>Chat-Name: </b>@{escape(chat_name)}\n'
            msg += f'<b>DC-ID: </b><code>{dc_id}</code>\n'
            msg += f'<b>Distance: </b><code>{distance}</code>\n'
        except Exception as e:
            msg += f'<b>If you want to know the chat information, please join the chat first!</b>\n'
    elif all([is_sudo, message.reply_to_message]):
        origin_message = message.reply_to_message
        if from_user := origin_message.forward_from:
            queried_id = from_user.id
            username = from_user.username or from_user.mention
            dc_id = from_user.dc_id
            msg += f'<b>User: </b>@{escape(username)}\n'
            msg += f'<b>User-ID: </b><code>{queried_id}</code>\n'
            msg += f'<b>DC-ID: </b><code>{dc_id}</code>\n'
        if chat := origin_message.forward_from_chat:
            chat_title = chat.title
            chat_id = chat.id
            chat_name = chat.username or "Unknown"
            dc_id = chat.dc_id
            distance = chat.distance
            msg += f'<b>Chat-Title: </b>{escape(chat_title)}\n'
            msg += f'<b>Chat-ID: </b><code>{chat_id}</code>\n'
            msg += f'<b>Chat-Name: </b>@{escape(chat_name)}\n'
            msg += f'<b>DC-ID: </b><code>{dc_id}</code>\n'
            msg += f'<b>Distance: </b><code>{distance}</code>\n'
        for media in [origin_message.photo, origin_message.video, origin_message.audio,
                      origin_message.voice, origin_message.sticker, origin_message.animation,
                      origin_message.video_note, origin_message.document]:
            if media and isinstance(media, tuple):
                file_id = media[0].file_id
                msg += f'<b>File-ID: </b><code>{file_id}</code>\n'
                break
            elif media:
                file_id = media.file_id
                msg += f'<b>File-ID: </b><code>{file_id}</code>\n'
                break
        if not msg:
            msg += f'<b>Unable to obtain valid information, it may be due to the user setting privacy protection \
                or invalid reply messages!</b>\n'
    else:
        from_user = message.from_user or message.sender_chat
        queried_id = from_user.id
        username = from_user.username or from_user.mention
        dc_id = from_user.dc_id
        msg += f'<b>User: </b>@{escape(username)}\n'
        msg += f'<b>User-ID: </b><code>{queried_id}</code>\n'
        msg += f'<b>DC-ID: </b><code>{dc_id}</code>\n'
        chat = message.chat
        if chat.type in [ChatType.SUPERGROUP, ChatType.GROUP] and is_sudo:
            chat_title = chat.title
            chat_id = chat.id
            chat_name = chat.username or "Unknown"
            dc_id = chat.dc_id
            distance = chat.distance
            msg += f'<b>GROUP-Title: </b>{escape(chat_title)}\n'
            msg += f'<b>GROUP-ID: </b><code>{chat_id}</code>\n'
            msg += f'<b>GROUP-Name: </b>@{escape(chat_name)}\n'
            msg += f'<b>DC-ID: </b><code>{dc_id}</code>\n'
            msg += f'<b>Distance: </b><code>{distance}</code>\n'
    
    reply_message = await sendMessage(message, msg)
    await auto_delete_message(message, reply_message, delay=30)

bot.add_handler(MessageHandler(info, filters=command(BotCommands.InfoCommand) & CustomFilters.authorized))
