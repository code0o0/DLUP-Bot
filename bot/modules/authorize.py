from asyncio import TimeoutError
import json
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from bot import user_data, bot, user, OWNER_ID, LOGGER
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.bot_utils import new_thread, update_user_ldata
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, auto_delete_message


async def get_buttons(from_user, key=None, text=None):
    user_id = from_user.id
    buttons = ButtonMaker()
    tgclient = user if user else bot
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
            msg = 'Send UserID or UserName to promote as Adminstator.\n'
            msg += 'Time out: 20 seconds'
        elif key == 'sudodl':
            msg = 'Send UserID or UserName to remove from Adminstator.\n'
            msg += 'Time out: 20 seconds'
        elif key == 'authadd':
            msg = 'Send UserID or UserName to authorize.\n'
            msg += 'Time out: 20 seconds'
        elif key == 'authdl':
            msg = 'Send UserID or UserName to unauthorize\n'
            msg += 'Time out: 20 seconds'
        elif key == 'list':
            msg = '<b>Authorized Users:</b> 👁️‍🗨️\n'
            if len(user_data) == 0:
                msg += 'No users are authorized'
            for _id in user_data.keys():
                LOGGER.info(_id)
                try:
                    queried_user = await tgclient.get_users(_id)
                    LOGGER.info(f'{_id} - {queried_user}')
                    username = queried_user.username if queried_user.username else queried_user.first_name
                except Exception as e:
                    LOGGER.error(e)
                    queried_chat = await tgclient.get_chat(_id)
                    username = queried_chat.username if queried_chat.username else queried_chat.title                    
                if user_data[_id].get('is_sudo'):
                    msg += f"<code>{username}</code>-<code>{_id}</code>-<b>Admin</b>\n"
                elif user_data[_id].get('is_auth'):
                    msg += f"<code>{username}</code>-<code>{_id}</code>-<b>Auther</b>\n"
                else:
                    msg += f"<code>{username}</code>-<code>{_id}</code>-<b>Group User</b>\n"
    elif text:
        msg = text
        buttons.ibutton('🔙Back', f'authset {user_id} back', position='footer')
        buttons.ibutton('🔚Close', f'authset {user_id} close', position='footer')  
    return msg, buttons.build_menu(2)


async def update_buttons(query, key=None, text=None):
    msg, button = await get_buttons(query.from_user, key, text)
    await editMessage(query.message, msg, button)

async def set_auth(client, query, key):
    user_id = query.from_user.id
    tgclient = user if user else bot
    try:
        response_message = await client.listen.Message(filters.regex(r'^[^/]'), id = filters.user(user_id), timeout = 20)
    except TimeoutError:
        LOGGER.info(f"Timeout for {user_id}")
        msg = 'Time out, please click the button to choose whether to return or close!'
        await update_buttons(query, 'authset', text=msg)
        return
    if response_message:
        value = response_message.text
    else:
        return
    if value.isdigit():
        queried_id = json.loads(value)
    else:
        value = value.split('t.me/')[-1]
        queried_id = value if value.startswith('@') else f'@{value}'
    try:
        queried_user = await tgclient.get_users(queried_id)
        value = queried_user.id
    except:
        value = ''
    if value == '':
        try:
            chat = await tgclient.get_chat(queried_id)
            value = chat.id
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
            await update_buttons(query, 'authset', text=msg)
            await deleteMessage(response_message)
    else:
        msg = 'UserID or UserName not found, please resend UserID or UserName!'
        reply_message = await response_message.reply(msg)
        await set_auth(client, query, key)
        await auto_delete_message(response_message, reply_message, 0)

@new_thread
async def auth_callback(client, query):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    if user_id != int(data[1]) and user_id != OWNER_ID:
        await query.answer('You are not allowed to do this', show_alert=True)
        return
    await client.listen.Cancel(filters.user(user_id))
    if data[2] == 'close':
        await query.answer()
        await auto_delete_message(message, message.reply_to_message, 0)
    elif data[2] == 'back':
        key = data[3] if len(data) == 4 else None
        await query.answer()
        await update_buttons(query, key)
    elif data[2] in ['sudoadd', 'sudodl', 'authadd', 'authdl']:
        key = data[2]
        await query.answer()
        await update_buttons(query, key)
        await set_auth(client, query, key)
    elif data[2] == 'list':
        await query.answer()
        await update_buttons(query, data[2])

async def authorize(client, message):
    msg, button = await get_buttons(message.from_user)
    await sendMessage(message, msg, button)


bot.add_handler(MessageHandler(authorize, filters=filters.command(BotCommands.AuthorizeCommand) & CustomFilters.sudo))
bot.add_handler(CallbackQueryHandler(auth_callback, filters=filters.regex("^authset") & CustomFilters.sudo))