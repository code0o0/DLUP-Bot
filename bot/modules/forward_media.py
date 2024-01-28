from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.enums import ParseMode, MessageMediaType
from pyrogram.types import InputMediaDocument, InputMediaPhoto, InputMediaVideo, InputMediaAudio
from html import escape
import re
from bot import bot, LOGGER
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import new_task

async def close_buttons(message, msg_dict):
    pass


async def forward_media(client, message):
    chat_id = message.chat.id
    command = message.command
    _dict = {
        'from_chat': None,
        'from_message_id': None,
        'forward_chat': None,
        'forward_number': None,
        'protect_content': False,
    }
    if len(command) > 1 and command[1].startswith('https://t.me/'):
        text, from_chat_id, from_message_id = command[1].rstrip('?single').rsplit('/', 2)
    elif from_message := message.reply_to_message:
        from_chat_id = from_message.forward_from_chat.id if from_message.forward_from_chat else ''
        from_message_id = from_message.forward_from_message_id
    else:
        msg = 'Please send <i>/forward</i> <u>https://t.me/channel_name/message_id</u> or '
        msg += 'forward a media message from the channel to the bot and reply to it with <i>/forward</i>'
        reply_message = await sendMessage(message, msg)
        await auto_delete_message(message, reply_message, delay=20)
        return
    _dict['from_chat'] = from_chat_id
    _dict['from_message_id'] = from_message_id
    await close_buttons(message, _dict)
    
    








    
bot.add_handler(MessageHandler(forward_media, filters=command(BotCommands.EditCommand) & CustomFilters.sudo))
