from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.enums import ParseMode, MessageMediaType
from pyrogram.types import InputMediaDocument, InputMediaPhoto, InputMediaVideo, InputMediaAudio
from html import escape

from bot import bot, user, LOGGER
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage, copyMedia, copyMediaGroup
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
        msg += '<i>/cmd caption -g number</i> to get the media group number.\n'
        msg += '<i>/cmd caption -i</i> to ignore the source of the message.\n'
        msg += '<i>/cmd caption -p</i> to protects the contents of the sent message from forwarding and saving.'
        reply_message = await sendMessage(message, msg)
        await auto_delete_message(client, [message, reply_message], 20)
        return
    caption = text.split('-g', 1)[0].split('-i', 1)[0].split('-p', 1)[0].strip()
    if not caption:
        caption = from_message.caption.html if from_message.caption else ''
    forward_chat = from_message.forward_from_chat
    ignore_source = True if '-i' in command else False
    protect_content = True if '-p' in command else False
    if forward_chat and not ignore_source:
        forward_chat_username = forward_chat.username
        forward_from_message_id = from_message.forward_from_message_id
        caption += f'\n🧿<b>From</b>👉 <a href="https://t.me/{forward_chat_username}/{forward_from_message_id}"><u>@{forward_chat_username}</u></a>'
 
    if '-g' in text:
        media_number = text.split('-g', 1)[1].split('-i', 1)[0].split('-p', 1)[0].strip()
        media_number = int(media_number) if media_number else 0
    else:
        media_number = 0
    if not from_message.media_group_id and media_number == 0:
        message_list = [from_message]
    elif from_message.media_group_id and media_number == 0:
        message_list = await client.get_media_group(chat_id, from_message.id)
    else:
        message_list = [from_message]
        message_ids = [from_message.id + i for i in range(1, 30)]
        if from_message.media in [MessageMediaType.PHOTO, MessageMediaType.VIDEO]:
            message_type = [MessageMediaType.PHOTO, MessageMediaType.VIDEO]
        else:
            message_type = [from_message.media]
        hestory_messages = await client.get_messages(chat_id, message_ids)
        for m in hestory_messages:
            if m.media in message_type:
                message_list.append(m)
            if len(message_list) >= media_number:
                break
    try:
        if len(message_list) == 1:
            await copyMedia(from_message, chat_id, caption, ParseMode.HTML, protect_content)
            await auto_delete_message(user, [message, from_message], 0)
            return
        send_medias = []
        for media_message in message_list:
            media = getattr(media_message, media_message.media.value)
            thumb = media.thumbs[0].file_id if media.thumbs else ''
            if media_message.media == MessageMediaType.VIDEO:
                input_media = InputMediaVideo(media.file_id, thumb=thumb)
            elif media_message.media == MessageMediaType.DOCUMENT:
                input_media = InputMediaDocument(media.file_id, thumb=thumb)
            elif media_message.media == MessageMediaType.AUDIO:
                input_media = InputMediaAudio(media.file_id, thumb=thumb)
            elif media_message.media == MessageMediaType.PHOTO:
                input_media = InputMediaPhoto(media.file_id)
            send_medias.append(input_media)
        group_count = (len(send_medias) + 10 - 1) // 10
        group_size = (len(send_medias) + group_count - 1) // group_count
        send_media_groups = [send_medias[i:i + group_size] for i in range(0, len(send_medias), group_size)]
        for send_media_group in send_media_groups:
            if caption:
                send_media_group[0].caption = caption
            send_media_group[0].parse_mode = ParseMode.HTML
            await copyMediaGroup(client, chat_id, send_media_group, protect_content)
        await auto_delete_message(client, [message, from_message], 0)
    except Exception as e:
        LOGGER.error(e)
        reply_message = await sendMessage(message, str(e))
        await auto_delete_message(client, [message, reply_message], 20)
 
    
bot.add_handler(MessageHandler(edit_media, filters=command(BotCommands.EditCommand) & CustomFilters.sudo))
