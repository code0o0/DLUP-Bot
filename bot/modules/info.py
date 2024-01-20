from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
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
            queried_id = text if text.startswith('@') else f'@{text}'
        try:
            user = await bot.get_users(queried_id)
            username = user.username or user.mention
            userid = user.id
            dcid = user.dc_id
            language_code = user.language_code
            msg += f'<b>User: </b>@{escape(username)}\n'
            msg += f'<b>User ID: </b><code>{userid}</code>\n'
            msg += f'<b>DC ID: </b><code>{dcid}</code>\n'
            msg += f'<b>Language Code: </b><code>{language_code}</code>\n'
        except Exception as e:
            msg += f'<b>User not found!</b>\n'
        reply_message = await sendMessage(message, msg)
        await auto_delete_message(message, reply_message, delay=30)
        return
    if is_sudo:
        origin_message = message.reply_to_message or message
    else:
        origin_message = message
    from_user = origin_message.forward_from or origin_message.from_user or origin_message.sender_chat
    queried_id = from_user.id
    username = from_user.username or from_user.mention
    msg += f'<b>User: </b>@{escape(username)}\n'
    msg += f'<b>UserID: </b><code>{queried_id}</code>\n'
    chat = origin_message.forward_from_chat or origin_message.chat
    chat_id = chat.id
    msg += f'<b>ChatID: </b><code>{chat_id}</code>\n'
    if chat_title := chat.title:
        msg += f'<b>ChatTitle: </b>{escape(chat_title)}\n'
    for media in [origin_message.photo, origin_message.video, origin_message.audio,
                  origin_message.voice, origin_message.sticker, origin_message.animation,
                  origin_message.video_note, origin_message.document]:
        if media and isinstance(media, tuple):
            file_id = media[0].file_id
            msg += f'<b>FileID: </b><code>{file_id}</code>\n'
            break
        elif media:
            file_id = media.file_id
            msg += f'<b>FileID: </b><code>{file_id}</code>\n'
            break

    reply_message = await sendMessage(message, msg)
    await auto_delete_message(message, reply_message, delay=30)

bot.add_handler(MessageHandler(info, filters=command(BotCommands.InfoCommand) & CustomFilters.authorized))
