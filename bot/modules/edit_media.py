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
async def edit_media(client, message):
    chat_id = message.chat.id
    text = message.text.split(' ', 1)[1] if len(message.text.split()) > 1 else ''
    command = message.command
    from_message = message.reply_to_message
    if not from_message or not from_message.media or from_message.poll:
        msg = 'Please use <i>/cmd caption</i> or <i>/cmd</i> to reply to the media message you want to edit!\n'
        msg += '<i>/cmd caption -i</i> to ignore the source of the message.\n'
        msg += '<i>/cmd caption -p</i> to protects the contents of the sent message from forwarding and saving.'
        reply_message = await sendMessage(message, msg)
        await auto_delete_message(client, [message, reply_message], 20)
        return
    protect_content = True if '-p' in command else False
    ignore_source = True if '-i' in command else False
    caption = text.split('-i', 1)[-1].split('-p', 1)[-1].strip()    
    try:
        if not caption:
            caption = from_message.caption.html if from_message.caption else ''
        forward_chat = from_message.forward_from_chat
        if forward_chat and not ignore_source:
            forward_chat_username = forward_chat.username
            forward_from_message_id = from_message.forward_from_message_id
            caption += f'\n🧿<b>From</b>👉 <a href="https://t.me/{forward_chat_username}/{forward_from_message_id}"><u>@{forward_chat_username}</u></a>'
        if from_message.media_group_id:
            # from_chat_id = from_message.chat.id
            # message_id = from_message.id
            # copy_message = await client.copy_media_group(chat_id, from_chat_id, message_id, captions=caption,
            #                                             parse_mode=ParseMode.HTML, protect_content=protect_content)
            media_group = await client.get_media_group(chat_id, from_message.id)
            send_medias = []
            for media_message in media_group:
                media = getattr(media_message, media_message.media.value)
                if media_message.media == MessageMediaType.VIDEO:
                    input_media = InputMediaVideo(media.file_id, thumb=media.thumbs[0].file_id)
                elif media_message.media == MessageMediaType.DOCUMENT:
                    input_media = InputMediaDocument(media.file_id, thumb=media.thumbs[0].file_id)
                elif media_message.media == MessageMediaType.AUDIO:
                    input_media = InputMediaAudio(media.file_id, thumb=media.thumbs[0].file_id)
                elif media_message.media == MessageMediaType.PHOTO:
                    input_media = InputMediaPhoto(media.file_id, thumb=media.thumbs[0].file_id)
                send_medias.append(input_media)
            if caption:
                send_medias[0].caption = caption
            send_medias[0].parse_mode = ParseMode.HTML
            await client.send_media_group(chat_id, send_medias, protect_content=protect_content)
        else:
            await from_message.copy(chat_id=chat_id, caption=caption, parse_mode=ParseMode.HTML,
                                    protect_content=protect_content)
        await auto_delete_message(client, [message, from_message], 0)
    except Exception as e:
        LOGGER.error(e)
        reply_message = await sendMessage(message, str(e))
        await auto_delete_message(client, [message, reply_message], 20)
    
bot.add_handler(MessageHandler(edit_media, filters=command(BotCommands.EditCommand) & CustomFilters.sudo))
