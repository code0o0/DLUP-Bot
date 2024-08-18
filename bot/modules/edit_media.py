from asyncio import sleep
from html import escape
from pyrogram import filters
from pyrogram.enums import ParseMode, MessageMediaType
from pyrogram.errors import ListenerTimeout, ListenerStopped
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InputMediaDocument, InputMediaPhoto, InputMediaVideo, InputMediaAudio
from bot import bot, OWNER_ID, LOGGER
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
    msg = '<b>Edit Media</b>\n'
    for key, value in msg_dict.items():
        msg += f'<u>{key}</u> is <b>{value}</b>\n'
    buttons.ibutton('Role', f'editset {user_id} role', position='header')
    buttons.ibutton('Provider', f'editset {user_id} provider', position='header')
    buttons.ibutton('Source', f'editset {user_id} source', position='header')
    buttons.ibutton('Tag', f'editset {user_id} tag', position='header')
    buttons.ibutton('Note', f'editset {user_id} note', position='header')
    buttons.ibutton('📝Caption', f'editset {user_id} caption', position='header')
    buttons.ibutton('📈Count', f'editset {user_id} count', position='header')
    buttons.ibutton('📩TgChat', f'editset {user_id} target', position='header')
    if msg_dict.get('protect'):
        buttons.ibutton('➰Protect', f'editset {user_id} protect', position='header')
    else:
        buttons.ibutton('🔰Protect', f'editset {user_id} protect', position='header')
    buttons.ibutton('🔥RUN', f'editset {user_id} run')
    buttons.ibutton('Close', f'editset {user_id} close', position='footer')
    button = buttons.build_menu(1, 3, 1)
    return msg, button

async def update_buttons(query, message_id):
    msg, button = await get_buttons(query.from_user, message_id)
    await editMessage(query.message, msg, button)

async def edit_media(client, message):
    message_id = message.reply_to_message_id
    msg_dict = handler_dict[message_id]
    del handler_dict[message_id]
    chat_id = msg_dict['chat_id']
    count = msg_dict['count']
    reply_message_id = msg_dict['reply_message_id']
    protect = msg_dict['protect']
    target_chat = msg_dict['target_chat']
    msg = ''
    if role := msg_dict['role']:
        msg += f'<b>主演:</b> {role}\n'
    if provider := msg_dict['provider']:
        msg += f'<b>厂商:</b> {provider}\n'
    if source := msg_dict['source']:
        msg += f'<b>来源:</b> {source}\n'
    if tag := msg_dict['tag']:
        msg += f'<b>标签:</b> {tag}\n'
    if note := msg_dict['note']:
        msg += f'<b>备注:</b> \n{note}'
    if caption := msg_dict['caption']:
        msg = (
            caption.replace('主演:', '<b>主演:</b>')
            .replace('厂商:', '<b>厂商:</b>').replace('来源:', '<b>来源:</b>')
            .replace('标签:', '<b>标签:</b>').replace('备注:', '<b>备注:</b>')
            )
    try:
        message_ids = [reply_message_id + i for i in range(30)]
        hestory_messages = await client.get_messages(chat_id, message_ids)
    except Exception as e:
        LOGGER.error(e)
        msg = f'<b>Status:</b> Get Message Failed\n'
        msg += f'<b>Reason:</b> {escape(str(e))}'
        err_message = await sendMessage(message, msg)
        await auto_delete_message(client, [message, message.reply_to_message, err_message], 20)
        return
    if hestory_messages[0].media in [MessageMediaType.PHOTO, MessageMediaType.VIDEO]:
        message_type = [MessageMediaType.PHOTO, MessageMediaType.VIDEO]
    else:
        message_type = [hestory_messages[0].media]
    message_list = []
    for m in hestory_messages:
        if m.media in message_type:
            message_list.append(m)
        if len(message_list) >= count:
            break
    if len(message_list) == 1:
        result = await copyMedia(message_list[0], target_chat, msg, ParseMode.HTML, protect)
        send_media_groups = []
    else:
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
    for smg in send_media_groups:
        smg[0].parse_mode = ParseMode.HTML
        if msg:
            smg[0].caption = msg
        result = await copyMediaGroup(client, target_chat, smg, protect)
        if result:
            break
        await sleep(0.5)
    if result:
        msg = f'<b>Status:</b> Send Failed\n'
        msg += f'<b>Reason:</b> {escape(result)}'
        err_message = await sendMessage(message, msg)
        await auto_delete_message(client, [message, message.reply_to_message, err_message], 20)
    else:
        message_list.extend([message, message.reply_to_message])
        await auto_delete_message(client, message_list, 0.5)

async def conversation_text(client, query, msg):
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    try:
        reply_text_message = await client.send_message(chat_id, msg)
        response_message = client.listen(
        chat_id=chat_id,
        user_id=user_id,
        filters=filters.regex(r'^[^/]'),
        timeout=30,
    )
    except ListenerTimeout:
        msg = 'Timeout, the conversation has been closed!'
        await editMessage(reply_text_message, msg)
        await auto_delete_message(client, reply_text_message, 20)
        return None
    except ListenerStopped:
        return None
    if response_message:
        response_text = response_message.text.strip()
        await auto_delete_message(client, [reply_text_message, response_message], 0.5)
    else:
        response_text = None
        await auto_delete_message(client, reply_text_message, 0.5)
    return response_text

@new_thread
async def edit_callback(client, query):
    user_id = query.from_user.id
    message = query.message
    cmd_message_id = message.reply_to_message_id
    data = query.data.split()
    if user_id != int(data[1]) and user_id != OWNER_ID:
        await query.answer('You are not allowed to do this', show_alert=True)
        return
    await client.stop_listening(chat_id=message.chat.id, user_id=user_id)
    if cmd_message_id not in handler_dict:
        await query.answer('This message has expired', show_alert=True)
        await auto_delete_message(client, [message, message.reply_to_message], 0)
        return
    if data[2] == 'close':
        await query.answer()
        del handler_dict[cmd_message_id]
        await auto_delete_message(client, [message, message.reply_to_message], 0)
    elif data[2] in ['role', 'provider', 'tag']:
        await query.answer()
        msg = f'Please send {data[2]} strings starting with #, separated by spaces between the two strings.\n<b>Timeout:</b> 30s.'
        response_text = await conversation_text(client, query, msg)
        if response_text is None:
            return
        response_text = response_text if response_text.upper() != 'NONE' else None
        handler_dict[cmd_message_id][data[2]] = response_text
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'source':
        await query.answer()
        msg = 'Please send the source of the media.\n<b>Timeout:</b> 30s.\n'
        msg += '<b>Note:</b> Please send a text or tg channel link.'
        response_text = await conversation_text(client, query, msg)
        if response_text is None:
            return
        if response_text.upper() == 'NONE':
            response_text = None
        elif response_text.startswith('https://t.me/'):
            chat_id = response_text.strip('https://t.me/').strip('https://t.me/c/').split('/')[0]
            chat_id = int(chat_id) if chat_id.isdigit() else chat_id
            chat = await client.get_chat(chat_id)
            response_text = f'<a href="{response_text}"><u>{chat.title}</u></a>'
        elif response_text.startswith(('http://', 'https://')):
            domain = response_text.split('//', 1)[-1].split('/', 1)[0]
            response_text = f'<a href="{response_text}"><u>{domain}</u></a>'
        handler_dict[cmd_message_id]['source'] = response_text
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'note':
        await query.answer()
        msg = 'Please send the note for the media.\n<b>Timeout:</b> 30s.'
        response_text = await conversation_text(client, query, msg)
        if response_text is None:
            return
        if response_text.upper() == 'NONE':
            response_text = None
        handler_dict[cmd_message_id]['note'] = response_text
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'caption':
        await query.answer()
        msg = 'Please send the caption for the media.\n<b>Timeout:</b> 30s.\n'
        msg += '<b>Note:</b> Caption will overwrite other descriptive information.'
        response_text = await conversation_text(client, query, msg)
        if response_text is None:
            return
        if response_text.upper() == 'NONE':
            response_text = None
        handler_dict[cmd_message_id]['caption'] = response_text
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'count':
        await query.answer()
        msg = 'Please send the number of media you want to edit.\n<b>Limit:</b> 30.\n<b>Timeout:</b> 30s.'
        response_text = await conversation_text(client, query, msg)
        if response_text is None:
            return
        handler_dict[cmd_message_id]['count'] = int(response_text) if response_text.isdigit() else 1
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'target':
        await query.answer()
        msg = 'Please send the chat id or username of the target chat.\n<b>Timeout:</b> 30s.'
        response_text = await conversation_text(client, query, msg)
        if response_text is None:
            return
        handler_dict[cmd_message_id]['target_chat'] = (
            int(response_text) if response_text.isdigit() else response_text
            )
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'protect':
        await query.answer()
        if handler_dict[cmd_message_id]['protect']:
            handler_dict[cmd_message_id]['protect'] = False
        else:
            handler_dict[cmd_message_id]['protect'] = True
        await update_buttons(query, cmd_message_id)
    elif data[2] == 'run':
        await query.answer()
        await editMessage(message, 'Sending media, please wait...')
        await sleep(0.5)
        await edit_media(client, message)

async def edit(client, message):
    message_id = message.id
    chat_id = message.chat.id
    handler_dict[message_id] = {
        'chat_id': chat_id,
        'reply_message_id': 0,
        'role': None,
        'provider': None,
        'source': None,
        'tag': None,
        'note': None,
        'caption': None,
        'count': 1,
        'target_chat': chat_id,
        'protect': False
    }
    reply_message = message.reply_to_message
    if reply_message and reply_message.media:
        reply_message_id = reply_message.id
        handler_dict[message_id]['reply_message_id'] = reply_message_id
    else:
        msg = 'Please reply to the media message you want to edit!'
        reply_message = await sendMessage(message, msg)
        await auto_delete_message(client, [message, reply_message], 20)
        return
    if from_chat := reply_message.forward_from_chat:
        from_message_id =reply_message.forward_from_message_id
        chat_link = (
            f"https://t.me/{from_chat.username}" if from_chat.username else f"https://t.me/c/{from_chat.id}"
            )
        handler_dict[message_id]["source"] = (
            f'<a href="{chat_link}/{from_message_id}"><u>{from_chat.title}</u></a>'
            )
    msg, button = await get_buttons(message.from_user, message_id)
    await sendMessage(message, msg, button)


bot.add_handler(MessageHandler(edit, filters=filters.command(BotCommands.EditCommand) & CustomFilters.sudo))
bot.add_handler(CallbackQueryHandler(edit_callback, filters=filters.regex("^editset") & CustomFilters.sudo))
