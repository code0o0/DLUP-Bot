from functools import partial
import json
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex, create
from time import time
from bot import user_data, bot, OWNER_ID
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.bot_utils import new_thread, update_user_ldata
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from asyncio import sleep, Lock

handler_dict = {}

async def get_buttons(from_user, key=None, text=None):
    user_id = from_user.id
    buttons = ButtonMaker()
    msg = ''
    if key is None:
        if user_id == OWNER_ID:
            msg = '<b>User Management</b> ⚙️'
            buttons.ibutton('👮Add admin', f'authset {user_id} sudoadd')
            buttons.ibutton('🤷Remove admin', f'authset {user_id} sudodl')
            buttons.ibutton('👷Add auther', f'authset {user_id} authadd')
            buttons.ibutton('💁Remove auther', f'authset {user_id} authdl')
            buttons.ibutton('👁️‍🗨️ List Users', f'authset {user_id} list')
        elif user_id in user_data and user_data[user_id].get('is_sudo'):
            msg = 'You are <b>Admin</b> 👮‍♂️'
            buttons.ibutton('👷Add auth', f'authset {user_id} authadd')
            buttons.ibutton('💁Remove auth', f'authset {user_id} authdl')
        buttons.ibutton('🔚Close', f'authset {user_id} close', position='footer')
    elif key in ['sudoadd', 'sudodl', 'authadd', 'authdl', 'list']:
        buttons.ibutton('🔙Back', f'authset {user_id} back', position='footer')
        buttons.ibutton('🔚Close', f'authset {user_id} close', position='footer')
        if key == 'sudoadd':
            msg = 'Send UserID or UserName to promote as Adminstator'
        elif key == 'sudodl':
            msg = 'Send UserID or UserName to remove from Adminstator'
        elif key == 'authadd':
            msg = 'Send UserID or UserName to authorize'
        elif key == 'authdl':
            msg = 'Send UserID or UserName to unauthorize'
        elif key == 'list':
            msg = '<b>Authorized Users:</b> 👁️‍🗨️\n'
            if len(user_data) == 0:
                msg += 'No users are authorized'
            for user in user_data.keys():
                user = await bot.get_users(user)
                username = user.username if user.username else user.first_name
                if user_data[user].get('is_sudo'):
                    msg += f"<code>{username}</code>-<code>{user}</code>-<b>Admin</b>\n"
                elif (not user_data[user].get('is_sudo')) and (user_data[user].get('is_auth')):
                    msg += f"<code>{username}</code>-<code>{user}</code>-<b>Auther</b>\n"
    elif text:
        msg = text
        buttons.ibutton('🔙Back', f'authset {user_id} back', position='footer')
        buttons.ibutton('🔚Close', f'authset {user_id} close', position='footer')  
    return msg, buttons.build_menu(2)


async def update_buttons(query, key=None, text=None):
    msg, button = await get_buttons(query.from_user, key, text)
    await editMessage(query.message, msg, button)


async def event_handler(client, query, pfunc, rfunc):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = time()
    async def event_filter(_, __, event):
        user = event.from_user.id or event.sender_chat
        return bool(user == user_id and event.text)
    handler = client.add_handler(MessageHandler(pfunc, filters=create(event_filter)), group=-1)
    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await rfunc()
    client.remove_handler(*handler)


async def set_auth(client, message, pre_event, key):
    user_id = pre_event.from_user.id
    value = message.text
    handler_dict[user_id] = False
    if value.isdigit():
        queried_id = json.loads(value)
    else:
        queried_id = value if value.startswith('@') else f'@{value}'
    try:
        user = await bot.get_users(queried_id)
        value = user.id
    except:
        value = ''
    if isinstance(value, int):
        if value == OWNER_ID:
            msg = '⚠ OWNER ID can\'t be changed'
        elif key == 'sudoadd':
            if value in user_data and user_data[value].get('is_sudo'):
                msg = 'User {} is already Sudo'.format(value)
            else:
                update_user_ldata(value, "is_sudo", True)
                await DbManager().update_user_data(value)
                msg = 'User {} is promoted as Adminstator'.format(value)
        elif key == 'sudodl':
            if value not in user_data or not user_data[value].get('is_sudo'):
                msg = 'User {} is not Sudo'.format(value)
            else:
                update_user_ldata(value, "is_sudo", False)
                update_user_ldata(value, "is_auth", True)
                await DbManager().update_user_data(value)
                msg = 'User {} is removed from Adminstator'.format(value)
        elif key == 'authadd':
            if value in user_data and user_data[value].get('is_sudo'):
                msg = 'User {} is already Sudo'.format(value)
            elif value in user_data and user_data[value].get('is_auth'):
                msg = 'User {} is already authorized'.format(value)
            else:
                update_user_ldata(value, "is_auth", True)
                await DbManager().update_user_data(value)
                msg = 'User {} is authorized'.format(value)
        elif key == 'authdl':
            if value not in user_data:
                msg = 'User {} is not authorized'.format(value)
            else:
                del user_data[value]
                await DbManager().update_user_data(value)
                msg = 'User {} is unauthorized'.format(value)
        if key in ['sudoadd', 'sudodl', 'authadd', 'authdl']:
            await update_buttons(pre_event, 'authset', text=msg)
            await message.delete()
    else:
        msg = 'UserID or UserName not found, please try again'
        await update_buttons(pre_event, 'authset', text=msg)
        pfunc = partial(set_auth, pre_event=pre_event, key=key)
        rfunc = partial(update_buttons, pre_event)
        await event_handler(client, pre_event, pfunc, rfunc)
        await message.delete()

@new_thread
async def auth_callback(client, query):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    if user_id != int(data[1]) or user_id != OWNER_ID:
        await query.answer('You are not allowed to do this', show_alert=True)
        return
    if data[2] == 'close':
        handler_dict[user_id] = False
        await query.answer()
        await message.reply_to_message.delete()
        await message.delete()
    elif data[2] == 'back':
        handler_dict[user_id] = False
        key = data[3] if len(data) == 4 else None
        await query.answer()
        await update_buttons(query, key)
    elif data[2] in ['sudoadd', 'sudodl', 'authadd', 'authdl']:
        handler_dict[user_id] = False
        await query.answer()
        await update_buttons(query, data[2])
        pfunc = partial(set_auth, pre_event=query, key=data[2])
        rfunc = partial(update_buttons, query)
        await event_handler(client, query, pfunc, rfunc)
    elif data[2] == 'list':
        handler_dict[user_id] = False
        await query.answer()
        await update_buttons(query, data[2])

async def authorize(client, message):
    msg, button = await get_buttons(message.from_user)
    await sendMessage(message, msg, button)


bot.add_handler(MessageHandler(authorize, filters=command(BotCommands.AuthorizeCommand) & CustomFilters.sudo))
bot.add_handler(CallbackQueryHandler(auth_callback, filters=regex("^authset") & CustomFilters.sudo))