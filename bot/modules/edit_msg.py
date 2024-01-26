from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.enums import ParseMode, MessageMediaType
from pyrogram.types import InputMediaDocument, InputMediaPhoto, InputMediaVideo, InputMediaAudio
from html import escape

from bot import bot, LOGGER
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import new_task

@new_task
async def edit_msg(client, message):
    chat_id = message.chat.id
    message_id = message.id
    caption = message.text.split(' ', 1)[1] if len(message.text.split()) > 1 else ''
    origin_message = message.reply_to_message
    forward_chat = origin_message.forward_from_chat
    if not origin_message or not origin_message.media or origin_message.poll:
        msg = 'Please use <i>/cmd caption</i> to reply to the media message you want to edit!'
        reply_message = await sendMessage(message, msg)
        await auto_delete_message(message, reply_message, delay=20)
        return
    try:
        if forward_chat:
            forward_chat_username = forward_chat.username
            forward_from_message_id = origin_message.forward_from_message_id
            caption += f'\nSOURCE: <a href="https://t.me/{forward_chat_username}/{forward_from_message_id}">{forward_chat_username}</a>'
        if origin_message.media_group_id:
            media_group = await client.get_media_group(chat_id, message_id)
            send_medias = []
            for media_message in media_group:
                media = getattr(origin_message, origin_message.media.value)
                if media_message.media == MessageMediaType.VIDEO:
                    InputMediaVideo(media.file_id, caption=caption, parse_mode=ParseMode.HTML)
                elif media_message.media == MessageMediaType.DOCUMENT:
                    InputMediaDocument(media.file_id, caption=caption, parse_mode=ParseMode.HTML)
                elif media_message.media == MessageMediaType.AUDIO:
                    InputMediaAudio(media.file_id, caption=caption, parse_mode=ParseMode.HTML)
                elif media_message.media == MessageMediaType.PHOTO:
                    InputMediaPhoto(media.file_id, caption=caption, parse_mode=ParseMode.HTML)
                send_medias.append(media)
            await client.send_media_group(chat_id, send_medias, protect_content=True)
        else:
            await origin_message.copy(chat_id=chat_id, caption=caption, parse_mode=ParseMode.HTML)
        await auto_delete_message(message, origin_message, delay=2)
    except Exception as e:
        LOGGER.error(e)
        reply_message = await sendMessage(message, str(e))
        await auto_delete_message(message, reply_message, delay=20)
    
bot.add_handler(MessageHandler(edit_msg, filters=command(BotCommands.EditCommand) & CustomFilters.sudo))
