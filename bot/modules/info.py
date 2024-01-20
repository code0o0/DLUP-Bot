#!/usr/bin/env python3
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from html import escape

from bot import bot, user_data
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
    if all([text, user_data[user_id].get('is_sudo')]):
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
    else:
        username = user.username or user.mention
        msg += f'<b>User: </b>@{escape(username)}\n'
        msg += f'<b>UserID: </b><code>{user_id}</code>\n'
        chat = message.chat
        if chat.type in ['group', 'supergroup']:
            group_id = chat.id
            msg += f'<b>GroupID: </b><code>{group_id}</code>\n'
        elif chat.type == 'channel':
            channel_id = chat.id
            msg += f'<b>ChannelID: </b><code>{channel_id}</code>\n'

    reply_message = await sendMessage(message, msg)
    await auto_delete_message(message, reply_message, delay=20)

bot.add_handler(MessageHandler(info, filters=command(BotCommands.InfoCommand) & CustomFilters.authorized))
