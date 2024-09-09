import json
from pyrogram import filters
from pyrogram.errors import ListenerTimeout, ListenerStopped
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from bot import user_data, bot, user, OWNER_ID
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import database
from bot.helper.ext_utils.bot_utils import update_user_ldata, new_task
from bot.helper.telegram_helper.message_utils import send_message, edit_message, delete_message, auto_delete_message


async def get_buttons(from_user, key=None, text=None):
    user_id = from_user.id
    buttons = ButtonMaker()
    tgclient = user or bot
    msg = ''
    if key is None:
        if user_id == OWNER_ID:
            msg = '<b>User Management</b> ⚙️'
            buttons.data_button('👮Add admin', f'authset {user_id} sudoadd')
            buttons.data_button('🤷Remove admin', f'authset {user_id} sudodl')
            buttons.data_button('👷Add auther', f'authset {user_id} authadd')
            buttons.data_button('💁Remove auther', f'authset {user_id} authdl')
            buttons.data_button('👁️‍🗨️ List Users', f'authset {user_id} list')
        elif user_id in user_data and user_data[user_id].get('is_sudo'):
            msg = 'You are <b>Admin</b> 👮‍♂️'
            buttons.data_button('👷Add auth', f'authset {user_id} authadd')
            buttons.data_button('💁Remove auth', f'authset {user_id} authdl')
        buttons.data_button('🔚Close', f'authset {user_id} close', position='footer')
    elif key in ['sudoadd', 'sudodl', 'authadd', 'authdl', 'list']:
        buttons.data_button('🔙Back', f'authset {user_id} back', position='footer')
        buttons.data_button('🔚Close', f'authset {user_id} close', position='footer')
        if key == 'sudoadd':
            msg = 'Send UserID or UserName to promote as Adminstator.\n'
            msg += '<b>Timeout:</b> 20s.'
        elif key == 'sudodl':
            msg = 'Send UserID or UserName to remove from Adminstator.\n'
            msg += '<b>Timeout:</b> 20s.'
        elif key == 'authadd':
            msg = 'Send UserID or UserName to authorize.\n'
            msg += '<b>Timeout:</b> 20s.'
        elif key == 'authdl':
            msg = 'Send UserID or UserName to unauthorize\n'
            msg += '<b>Timeout:</b> 20s.'
        elif key == 'list':
            msg = '<b>Authorized Users:</b> 👁️‍🗨️\n'
            if len(user_data) == 0:
                msg += 'No users are authorized'
            for _id in user_data.keys():
                try:
                    queried_chat = await tgclient.get_chat(_id)
                    username = queried_chat.username if queried_chat.username else queried_chat.first_name
                except Exception:
                    username = _id                   
                if user_data[_id].get('is_sudo'):
                    msg += f"<code>{username}</code>-<code>{_id}</code>-<b>Admin</b>\n"
                elif user_data[_id].get('is_auth'):
                    msg += f"<code>{username}</code>-<code>{_id}</code>-<b>Auther</b>\n"
                else:
                    msg += f"<code>{username}</code>-<code>{_id}</code>-<b>Group User</b>\n"
    elif text:
        msg = text
        buttons.data_button('🔙Back', f'authset {user_id} back', position='footer')
        buttons.data_button('🔚Close', f'authset {user_id} close', position='footer')  
    return msg, buttons.build_menu(2)


async def update_buttons(query, key=None, text=None):
    msg, button = await get_buttons(query.from_user, key, text)
    await edit_message(query.message, msg, button)


async def set_auth(client, query, key):
    message = query.message
    from_user = query.from_user
    try:
        response_message = await client.listen(
            chat_id=message.chat.id,
            user_id=from_user.id,
            filters=filters.regex(r'^[^/]'),
            timeout=30,
    )
    except ListenerTimeout:
        msg = 'Timeout, the conversation has been closed!'
        await update_buttons(query, 'authset', text=msg)
        return
    except ListenerStopped:
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
        tgclient = user or bot
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
                await database.update_user_data(value)
                msg = 'User {} is promoted as Adminstator'.format(value)
        elif key == 'sudodl':
            if value not in user_data or not user_data[value].get('is_sudo'):
                msg = 'User {} is not Sudo'.format(value)
            else:
                update_user_ldata(value, "is_sudo", False)
                update_user_ldata(value, "is_auth", True)
                await database.update_user_data(value)
                msg = 'User {} is removed from Adminstator'.format(value)
        elif key == 'authadd':
            if value in user_data and user_data[value].get('is_sudo'):
                msg = 'User {} is already Sudo'.format(value)
            elif value in user_data and user_data[value].get('is_auth'):
                msg = 'User {} is already authorized'.format(value)
            else:
                update_user_ldata(value, "is_auth", True)
                await database.update_user_data(value)
                msg = 'User {} is authorized'.format(value)
        elif key == 'authdl':
            if value not in user_data:
                msg = 'User {} is not authorized'.format(value)
            else:
                del user_data[value]
                await database.update_user_data(value)
                msg = 'User {} is unauthorized'.format(value)
        if key in ['sudoadd', 'sudodl', 'authadd', 'authdl']:
            await update_buttons(query, 'authset', text=msg)
            await delete_message(response_message)
    else:
        msg = 'UserID or UserName not found, please resend UserID or UserName!'
        reply_message = await response_message.reply(msg)
        await set_auth(client, query, key)
        await auto_delete_message(client, [response_message, reply_message], 0)

@new_task
async def auth_callback(client, query):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    if user_id != int(data[1]) and user_id != OWNER_ID:
        await query.answer('You are not allowed to do this', show_alert=True)
        return
    await client.stop_listening(
        chat_id=message.chat.id,
        user_id=user_id,
        )
    if data[2] == 'close':
        await query.answer()
        await auto_delete_message(client, [message, message.reply_to_message], 0)
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

@new_task
async def authorize(client, message):
    msg, button = await get_buttons(message.from_user)
    await send_message(message, msg, button)

bot.add_handler(
    MessageHandler(
        authorize,
        filters=filters.command(BotCommands.AuthorizeCommand, case_sensitive=True)
        & CustomFilters.sudo,
    )
)

bot.add_handler(
    CallbackQueryHandler(
        auth_callback,
        filters=filters.regex("^authset")
        & CustomFilters.sudo,
    )
)