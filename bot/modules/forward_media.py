from pyrogram.handlers import MessageHandler
from pyrogram import filters
from pyrogram.enums import ParseMode, MessageMediaType
from pyrogram.types import InputMediaDocument, InputMediaPhoto, InputMediaVideo, InputMediaAudio
from asyncio import TimeoutError
from html import escape
from bot import bot, OWNER_ID, LOGGER
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage, editMessage, deleteMessage

handler_dict = {}

async def update_buttons(message):
    buttons = ButtonMaker()
    from_user_id = message.from_user.id
    msg_dict = handler_dict[from_user_id]
    _dict = {
        'from_chat': None,
        'from_message_id': None,
        'forward_chat': None,
        'forward_number': 1,
        'protect_content': False,
    }
    _dict.update(msg_dict)
    msg = '<b>Forward Media</b>\n'
    for key, value in _dict.items():
        msg += f'<u>{key}</u> is <b>{value}</b>\n'
    if msg_dict.get('forward_chat'):
        buttons.ibutton('RUN ✅', f'forwardset {from_user_id} run')
        if len(msg_dict) < 5:
            buttons.ibutton('CONTINUE ⏩ ', f'forwardset {from_user_id} continue')
    buttons.ibutton('Close', f'forwardset {from_user_id} close', position='footer')
    button = buttons.build_menu(1, 1, 1)
    return msg, button

async def conversation_text(client, reply_button_message, reply_text_message):
    chat_id = reply_button_message.chat.id
    message_id = reply_button_message.id
    user_id = reply_button_message.from_user.id
    try:
        response_message = await client.listen.Message(filters=filters.regex(r'^[^/]') & filters.user(user_id) &
                                                       filters.chat(chat_id), id=f'{chat_id}-{message_id}', timeout=20)
    except TimeoutError:
        msg = 'Time out, please click the button to close conversation.'
        await editMessage(reply_text_message, msg)
        await auto_delete_message(cmd_message=reply_text_message, delay=20)
        return None
    response_text = response_message.text
    await deleteMessage(response_message)
    return response_text

async def set_forward_pars(client, reply_button_message):
    chat_id = reply_button_message.chat.id
    user_id = reply_button_message.from_user.id
    msg_dict = handler_dict[user_id]
    if 'forward_chat' not in msg_dict:
        msg = 'Please send the chat ID or Username you want to forward to.\nTimeout in 20 seconds.'
        reply_text_message = client.send_message(chat_id=chat_id, text=msg)
        response_text = await conversation_text(client, reply_button_message, reply_text_message)
        if response_text is None:
            return
        elif response_text.isdigit():
            handler_dict[user_id]['forward_chat'] = int(response_text)
        else:
            handler_dict[user_id]['forward_chat'] = response_text if response_text.startswith('@') else f'@{response_text}'
        await update_buttons(reply_button_message)
    elif 'forward_number' not in msg_dict:
        msg = 'Please send the number of messages you want to forward.\nTimeout in 20 seconds.'
        await editMessage(reply_text_message, msg)
        response_text = await conversation_text(client, reply_button_message, reply_text_message)
        if response_text is None:
            return
        handler_dict[user_id]['forward_number'] = int(response_text) if response_text.isdigit() else 1
        await update_buttons(reply_button_message)
    elif 'protect_content' not in msg_dict:
        msg = 'Do you want to protect the content? True or False.\nTimeout in 20 seconds.'
        await editMessage(reply_text_message, msg)
        response_text = await conversation_text(client, reply_button_message, reply_text_message)
        if response_text is None:
            return
        handler_dict[user_id]['protect_content'] = True if response_text.lower() == 'true' else False
        await update_buttons(reply_button_message)

async def forward_message(message):
    user_id = message.from_user.id
    await editMessage(message, 'Forwarding completed.')
    del handler_dict[user_id]
    await auto_delete_message(message, message.reply_to_message, 20)
    pass
    




async def button_callback(client, query):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    chat_id = message.chat.id
    query_id = query.id
    if user_id != int(data[1]) and user_id != OWNER_ID:
        await query.answer('You are not allowed to do this', show_alert=True)
        return
    await client.listen.Cancel(f'{chat_id}-{query_id}')
    if data[2] == 'close':
        await query.answer()
        del handler_dict[user_id]
        await auto_delete_message(message, message.reply_to_message, 0)
    elif data[2] == 'run':
        await query.answer('Forwarding...', show_alert=True)
        await forward_message(message)
    elif data[2] == 'continue':
        await query.answer()
        await set_forward_pars(client, message)

async def forward(client, message):
    command = message.command
    user_id = message.from_user.id
    handler_dict[user_id] = {}
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
        await auto_delete_message(message, reply_message, delay=20)
        return
    handler_dict[user_id]['from_chat'] = from_chat_id
    handler_dict[user_id]['from_message_id'] = from_message_id
    msg, button = await update_buttons(message)
    reply_button_message = await sendMessage(message, msg, button)
    await set_forward_pars(client, reply_button_message)



    
# bot.add_handler(MessageHandler(forward, filters=command(BotCommands.EditCommand) & CustomFilters.sudo))
