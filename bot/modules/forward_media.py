from asyncio import TimeoutError, sleep
from html import escape
import random
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram import filters
from pyrogram.enums import ParseMode, MessageMediaType
from pyrogram.types import InputMediaDocument, InputMediaPhoto, InputMediaVideo, InputMediaAudio
from bot import bot, OWNER_ID, LOGGER, user
from bot.helper.ext_utils.bot_utils import new_thread
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (auto_delete_message, sendMessage, editMessage,
                                                      copyMedia, copyMediaGroup)

handler_dict = {}

async def get_buttons(from_user, message_id):
    buttons = ButtonMaker()
    user_id = from_user.id
    msg_dict = handler_dict[message_id]
    msg = '<b>Forward Media</b>\n'
    for key, value in msg_dict.items():
        msg += f'<u>{key}</u> is <b>{value}</b>\n'
    buttons.ibutton('Forward Chat🎫', f'forwardset {user_id} forward_chat', position='header')
    buttons.ibutton('Forward Number📑', f'forwardset {user_id} forward_number', position='header')
    buttons.ibutton('Protect Content🔒', f'forwardset {user_id} protect_content', position='header')
    buttons.ibutton('RUN✅', f'forwardset {user_id} run')
    buttons.ibutton('Close', f'forwardset {user_id} close', position='footer')
    button = buttons.build_menu(1, 2, 1)
    return msg, button

async def update_buttons(query, message_id):
    msg, button = await get_buttons(query.from_user, message_id)
    await editMessage(query.message, msg, button)

async def forward_message(client, message, message_id):
    msg_dict = handler_dict[message_id]
    del handler_dict[message_id]
    from_chat = msg_dict['from_chat']
    from_message_id = msg_dict['from_message_id']
    forward_chat = msg_dict['forward_chat']
    forward_number = msg_dict['forward_number']
    protect_content = msg_dict['protect_content']
    messages_id_list = [from_message_id + i for i in range(forward_number)]
    msg = f'<pre> Forward Task: from {from_chat} to {forward_chat}</pre>\n'
    try:
        message_list = await client.get_messages(from_chat, messages_id_list)
    except Exception as e:
        try:
            message_list = user.get_messages(from_chat, messages_id_list)
        except Exception as e:
            LOGGER.error(e) 
            msg += f'<pre>Status: Failed</pre>\n'
            msg += f'<b>Reason:</b> {escape(str(e))}'
            error_message = await sendMessage(message, msg)
            await auto_delete_message(client, [message, error_message], 20)
            return
    if not message_list:
        msg += f'<pre>Status: Failed</pre>\n'
        msg += f'<b>Reason:</b> No message found!'
        error_message = await sendMessage(message, msg)
        await auto_delete_message(client, [message, error_message], 20)
        return
    media_messages = {}
    for message in message_list:
        if not message.media:
            continue
        if not message.media_group_id:
            media_messages[message.id] = [message]
        elif message.media_group_id not in media_messages:
            media_messages[message.media_group_id] = [message]
        else:
            media_messages[message.media_group_id].append(message)
    for messages in media_messages.values():
        if len(messages) == 1:
            message = messages[0]
            caption = message.caption.html if message.caption else ''
            result = await copyMedia(message, forward_chat, caption, ParseMode.HTML, protect_content)
        else:
            send_medias = []
            for message in messages:
                media = getattr(message, message.media.value)
                if message.media == MessageMediaType.VIDEO:
                    input_media = InputMediaVideo(media.file_id, thumb=media.thumbs[0].file_id)
                elif message.media == MessageMediaType.DOCUMENT:
                    input_media = InputMediaDocument(media.file_id, thumb=media.thumbs[0].file_id)
                elif message.media == MessageMediaType.AUDIO:
                    input_media = InputMediaAudio(media.file_id, thumb=media.thumbs[0].file_id)
                elif message.media == MessageMediaType.PHOTO:
                    input_media = InputMediaPhoto(media.file_id, thumb=media.thumbs[0].file_id)
                send_medias.append(input_media)
            caption = messages[0].caption.html if messages[0].caption else ''
            if caption:
                send_medias[0].caption = caption
            send_medias[0].parse_mode = ParseMode.HTML
            result = await copyMediaGroup(client, forward_chat, send_medias, protect_content)
        if result:
            msg += f'<pre>Status: Failed</pre>\n'
            msg += f'<b>Reason:</b> {escape(result)}'
            error_message = await sendMessage(message, msg)
            await auto_delete_message(client, [message, error_message], 20)
            return
        await sleep(1 + random.random())
    msg += f'<pre>Status: Success</pre>\n'
    success_message = await sendMessage(message, msg)
    await auto_delete_message(client, [message, success_message], 20)
    
async def conversation_text(client, query, reply_text_message):
    chat_id = reply_text_message.chat.id
    message_id = query.message.id
    user_id = query.from_user.id
    try:
        response_message = await client.listen.Message(filters=filters.regex(r'^[^/]') & filters.user(user_id) &
                                                       filters.chat(chat_id), id=f'{message_id}', timeout=20)
    except TimeoutError:
        msg = 'Timeout, the conversation has been closed!'
        await editMessage(reply_text_message, msg)
        await auto_delete_message(client, reply_text_message, 20)
        return None
    if response_message:
        response_text = response_message.text
    else:
        response_text = None
    await auto_delete_message(client, [reply_text_message, response_message], 0)
    return response_text

@new_thread
async def forward_callback(client, query):
    user_id = query.from_user.id
    message = query.message
    cmd_message_id = message.reply_to_message_id
    callback_message_id = message.id
    data = query.data.split()
    if user_id != int(data[1]) and user_id != OWNER_ID:
        await query.answer('You are not allowed to do this', show_alert=True)
        return
    await client.listen.Cancel(f'{callback_message_id}')
    if cmd_message_id not in handler_dict:
        await query.answer('This message has expired', show_alert=True)
        await auto_delete_message(client, [message, message.reply_to_message], 0)
        return
    if data[2] == 'close':
        await query.answer()
        del handler_dict[cmd_message_id]
        await auto_delete_message(client, [message, message.reply_to_message], 0)
    elif data[2] == 'forward_chat':
        await query.answer()
        msg = 'Please send the chat ID or Username you want to forward to.\n<b>Timeout:</b> 20s.'
        reply_text_message = await client.send_message(message.chat.id, msg)
        response_text = await conversation_text(client, query, reply_text_message)
        if response_text is None:
            return
        elif response_text.isdigit():
            handler_dict[cmd_message_id]['forward_chat'] = int(response_text)
        else:
            handler_dict[cmd_message_id]['forward_chat'] = response_text if response_text.startswith('@') else f'@{response_text}'
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'forward_number':
        await query.answer()
        msg = 'Please send the number of messages you want to forward.\n<b>Timeout:</b> 20s.'
        reply_text_message = await client.send_message(message.chat.id, msg)
        response_text = await conversation_text(client, query, reply_text_message)
        if response_text is None:
            return
        handler_dict[cmd_message_id]['forward_number'] = int(response_text) if response_text.isdigit() else 1
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'protect_content':
        await query.answer()
        msg = 'Do you want to protect the content? True or False.\n<b>Timeout:</b> 20s.'
        reply_text_message = await client.send_message(message.chat.id, msg)
        response_text = await conversation_text(client, query, reply_text_message)
        if response_text is None:
            return
        handler_dict[cmd_message_id]['protect_content'] = True if response_text.lower() == 'true' else False
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'run':
        await query.answer()
        msg = '🚴Forwarding...'
        message = await editMessage(message, msg)
        await forward_message(client, message, cmd_message_id)

async def forward(client, message):
    command = message.command
    message_id = message.id
    handler_dict[message_id] = {
        'from_chat': None,
        'from_message_id': None,
        'forward_chat': 'me',
        'forward_number': 1,
        'protect_content': False,
    }
    if len(command) > 1 and command[1].startswith('https://t.me/'):
        _, from_chat_id, from_message_id = command[1].rstrip('?single').rsplit('/', 2)
    elif from_message := message.reply_to_message:
        # from_chat_id = from_message.forward_from_chat.id if from_message.forward_from_chat else ''
        # from_message_id = from_message.forward_from_message_id
        from_chat_id = from_message.chat.id
        from_message_id = from_message.id
    else:
        msg = 'Please send <i>/forward</i> <u>https://t.me/channel_name/message_id</u> or '
        msg += 'forward a media message from the channel to the bot and reply to it with <i>/forward</i>'
        reply_message = await sendMessage(message, msg)
        await auto_delete_message(client, [message, reply_message], 20)
        return
    handler_dict[message_id]['from_chat'] = from_chat_id
    handler_dict[message_id]['from_message_id'] = from_message_id
    msg, button = await get_buttons(message.from_user, message_id)
    await sendMessage(message, msg, button)


bot.add_handler(MessageHandler(forward, filters=filters.command(BotCommands.ForwardCommand) & CustomFilters.sudo))
bot.add_handler(CallbackQueryHandler(forward_callback, filters=filters.regex("^forwardset") & CustomFilters.sudo))
