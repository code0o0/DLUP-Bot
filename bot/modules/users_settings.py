from asyncio import create_subprocess_exec
from configparser import ConfigParser
from html import escape
from os import getcwd
from PIL import Image

from aiofiles.os import remove
from aiofiles.os import path as aiopath
from aioshutil import rmtree as aiormtree
from pyrogram import filters
from pyrogram.errors import ListenerStopped, ListenerTimeout
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import (
    IS_PREMIUM_USER,
    OWNER_ID,
    bot,
    user_data,
    LOGGER,
)
from ..helper.ext_utils.bot_utils import (
    get_size_bytes,
    new_task,
    update_user_ldata,
    sync_to_async,
)
from ..helper.ext_utils.db_handler import database
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    auto_delete_message,
    edit_message,
    send_message,
)


async def get_buttons(from_user, edit_type=None, key=None):
    user_id = from_user.id
    name = from_user.mention
    user_dict = user_data.get(user_id, {})
    buttons = ButtonMaker()
    if edit_type is None:
        buttons.data_button("Aria Options", "userset {user_id} aria")
        buttons.data_button("Yt-dlp Options", "userset {user_id} yt-dlp")
        buttons.data_button("Upload Options", "userset {user_id} upload")
        buttons.data_button("Leech Config", "userset {user_id} leech")
        buttons.data_button("Rclone Config", "userset {user_id} rclone")
        buttons.data_button("Gdrive Config", "userset {user_id} gdrive")
        buttons.data_button("Close", "userset {user_id} close", position="footer")
        msg = f"User Settings for {name}:"
    elif edit_type in ["aria", "yt-dlp", "upload", "leech", "rclone", "gdrive"]:
        buttons.data_button("Back", f"userset {user_id} back", position="footer")
        buttons.data_button("Close", f"userset {user_id} close", position="footer")
        msg = f"{edit_type.capitalize()} Settings for {name}:\n"
        if edit_type == "aria":
            aria2_user_dict = user_dict.get("aria2_user")
            for index, key in enumerate(list(aria2_user_dict.keys()), start=1):
                value = (
                    str(aria2_user_dict[key]) if str(aria2_user_dict[key]) else "None"
                )
                msg += f"{index}. <b>{key}</b> is <u>{value}</u>\n"
                buttons.data_button(
                    index, f"userset {user_id} ariavar {key}", position="header"
                )
            buttons.data_button(
                "Add Key", f"userset {user_id} ariavar_key", position="body"
            )
            buttons.data_button(
                "Default", f"userset {user_id} ariavar_reset", position="body"
            )
            msg += "\nSelect the option to edit."
        elif edit_type == "yt-dlp":
            msg += (
                f"Current value is <u>escape({user_dict.get('yt_user', 'None')})</u>\n"
            )
            buttons.data_button(
                "Edit YT-DLP Options", f"userset {user_id} ytedit", position="body"
            )
            msg += "\nClick to edit."
        elif edit_type == "upload":
            upload_user_dict = user_dict.get("upload_user")
            del upload_user_dict["path_shortcuts"]
            for index, key in enumerate(list(upload_user_dict.keys()), start=1):
                value = (
                    str(upload_user_dict[key]) if str(upload_user_dict[key]) else "None"
                )
                msg += f"{index}. <b>{key}</b> is <u>{value}</u>\n"
                buttons.data_button(
                    index, f"userset {user_id} upvar {key}", position="header"
                )
            buttons.data_button(
                "Path Shortcuts", f"userset {user_id} pathshort", position="body"
            )
            msg += "Select the option to edit."
        elif edit_type == "leech":
            leech_user_dict = user_dict.get("leech_user")
            for index, key in enumerate(list(leech_user_dict.keys()), start=1):
                value = (
                    str(leech_user_dict[key]) if str(leech_user_dict[key]) else "None"
                )
                msg += f"{index}. <b>{key}</b> is <u>{value}</u>\n"
                buttons.data_button(
                    index, f"userset {user_id} lhvar {key}", position="header"
                )
            buttons.data_button(
                "Default", f"userset {user_id} lhvar_reset", position="body"
            )
            msg += "Select the option to edit."
        elif edit_type == "rclone":
            rclone_user_dict = user_dict.get("rclone_user")
            for index, key in enumerate(list(rclone_user_dict.keys()), start=1):
                value = (
                    str(rclone_user_dict[key]) if str(rclone_user_dict[key]) else "None"
                )
                msg += f"{index}. <b>{key}</b> is <u>{value}</u>\n"
                buttons.data_button(
                    index, f"userset {user_id} rcvar {key}", position="header"
                )
            buttons.data_button(
                "Set Config", f"userset {user_id} rcvar setconf", position="body"
            )
            if not await aiopath.exists(f"rclone/{user_id}.conf"):
                msg += "<b>WARNING:</b> Rclone Config is <b>Not Exists</b>\n"
            msg += "Select the option to edit."
        elif edit_type == "gdrive":
            gdrive_user_dict = user_dict.get("gdrive_user")
            for index, key in enumerate(list(gdrive_user_dict.keys()), start=1):
                value = (
                    str(gdrive_user_dict[key]) if str(gdrive_user_dict[key]) else "None"
                )
                msg += f"{index}. <b>{key}</b> is <u>{value}</u>\n"
                buttons.data_button(
                    index, f"userset {user_id} gdvar {key}", position="header"
                )
            buttons.data_button(
                "Set Credentials", f"userset {user_id} gdvar setcred", position="body"
            )
            if not await aiopath.exists(f"tokens/{user_id}.pickle") and (
                not await aiopath.exists(f"tokens/{user_id}-accounts")
            ):
                msg += "<b>WARNING:</b> Gdrive Credentials is <b>Not Exists</b>\n"
            msg += "Select the option to edit."
    elif edit_type == "pathshort":
        buttons.data_button("Back", f"userset {user_id} upload", position="footer")
        buttons.data_button("Close", f"userset {user_id} close", position="footer")
        msg = "Path Shortcuts Settings for {name}:\n"
        upload_user_dict = user_dict.get("upload_user")
        path_shortcuts = upload_user_dict.get("path_shortcuts")
        for index, key in enumerate(list(path_shortcuts.keys()), start=1):
            value = str(path_shortcuts[key]) if str(path_shortcuts[key]) else "None"
            msg += f"{index}. <b>{key}</b> is <u>{value}</u>\n"
            buttons.data_button(
                index, f"userset {user_id} psvar {key}", position="header"
            )
        buttons.data_button(
            "Add Shortcut", f"userset {user_id} psvar_add", position="body"
        )
        if not path_shortcuts:
            msg += "Path Shortcuts are <b>Not Settings</b>\n"
        msg += "Select the option to edit."

    elif edit_type in ["ariavar", "upvar", "lhvar", "rcvar", "gdvar", "psvar"]:
        if edit_type == "ariavar":
            aria2_user_dict = user_dict.get("aria2_user")
            value = str(aria2_user_dict[key]) if str(aria2_user_dict[key]) else "None"
            msg = f"Edit <b>{key}</b> for {name}:\n"
            msg += f"Current value is <u>{value}</u>\n\n"
            msg += "Click the button to edit."
            buttons.data_button(
                "Edit", f"userset {user_id} ariaedit {key}", position="body"
            )
            buttons.data_button("Back", f"userset {user_id} aria", position="footer")
            buttons.data_button("Close", f"userset {user_id} close", position="footer")
        elif edit_type == "upvar":
            upload_user_dict = user_dict.get("upload_user")
            value = str(upload_user_dict[key]) if str(upload_user_dict[key]) else "None"
            msg = f"Edit <b>{key}</b> for {name}:\n"
            msg += f"Current value is <u>{value}</u>\n\n"
            msg += "Click the button to edit."
            if key == "upload_type":
                if value == "Gdrive":
                    buttons.data_button(
                        "Change to Rclone",
                        f"userset {user_id} upedit {key}",
                        position="body",
                    )
                else:
                    buttons.data_button(
                        "Change to Gdrive",
                        f"userset {user_id} upedit {key}",
                        position="body",
                    )
            else:
                buttons.data_button(
                    "Edit", f"userset {user_id} upedit {key}", position="body"
                )
            buttons.data_button("Back", f"userset {user_id} upload", position="footer")
            buttons.data_button("Close", f"userset {user_id} close", position="footer")
        elif edit_type == "lhvar":
            leech_user_dict = user_dict.get("leech_user")
            value = str(leech_user_dict[key]) if str(leech_user_dict[key]) else "None"
            msg = f"Edit <b>{key}</b> for {name}:\n"
            msg += f"Current value is <u>{escape(value)}</u>\n\n"
            msg += "Click the button to edit."
            if key == "leech_type":
                if value == "Media":
                    buttons.data_button(
                        "Change to Document",
                        f"userset {user_id} lhedit {key}",
                        position="body",
                    )
                else:
                    buttons.data_button(
                        "Change to Media",
                        f"userset {user_id} lhedit {key}",
                        position="body",
                    )
            elif key in ["equal_splits", "media_group", "mixed_leech"]:
                if value == "True":
                    buttons.data_button(
                        "Disable", f"userset {user_id} lhedit {key}", position="body"
                    )
                else:
                    buttons.data_button(
                        "Enable", f"userset {user_id} lhedit {key}", position="body"
                    )
            elif key == "custom_thumb":
                if value == "Not Exists":
                    buttons.data_button(
                        "Add Thumb", f"userset {user_id} lhedit {key}", position="body"
                    )
                else:
                    buttons.data_button(
                        "Delete Thumb",
                        f"userset {user_id} lhedit {key}",
                        position="body",
                    )
            elif key == "leech_method":
                if value == "User":
                    buttons.data_button(
                        "Change to Bot",
                        f"userset {user_id} lhedit {key}",
                        position="body",
                    )
                else:
                    buttons.data_button(
                        "Change to User",
                        f"userset {user_id} lhedit {key}",
                        position="body",
                    )
            else:
                buttons.data_button(
                    "Edit", f"userset {user_id} lhedit {key}", position="body"
                )
            buttons.data_button("Back", f"userset {user_id} leech", position="footer")
            buttons.data_button("Close", f"userset {user_id} close", position="footer")

        elif edit_type == "rcvar":
            if key == "setconf":
                if await aiopath.exists(f"rclone/{user_id}.conf"):
                    buttons.data_button(
                        "Delete Config",
                        f"userset {user_id} rcedit_del",
                        position="body",
                    )
                else:
                    buttons.data_button(
                        "Add Config", f"userset {user_id} rcedit_add", position="body"
                    )
            else:
                rclone_user_dict = user_dict.get("rclone_user")
                value = (
                    str(rclone_user_dict[key]) if str(rclone_user_dict[key]) else "None"
                )
                msg = f"Edit <b>{key}</b> for {name}:\n"
                msg += f"Current value is <u>{value}</u>\n\n"
                if key == "remote":
                    config = ConfigParser()
                    if await aiopath.exists(f"rclone/{user_id}.conf"):
                        config.read(f"rclone/{user_id}.conf")
                    else:
                        msg += "<b>WARNING:</b> Rclone Config is <b>Not Exists</b>\n"
                    remotes = config.sections()
                    for remote in remotes:
                        if remote == value:
                            buttons.data_button(
                                f"{remote} ✅",
                                f"userset {user_id} rcedit_remote {remote}",
                                position="body",
                            )
                        buttons.data_button(
                            remote,
                            f"userset {user_id} rcedit_remote {remote}",
                            position="body",
                        )
                elif key == "gdrive_sa":
                    if not await aiopath.exists(f"tokens/{user_id}-accounts"):
                        msg += "<b>WARNING:</b> Gdrive Service Accounts is <b>Not Exists</b>\n"
                    if value == "True":
                        buttons.data_button(
                            "Disable Service Accounts",
                            f"userset {user_id} rcedit {key}",
                            position="body",
                        )
                    else:
                        buttons.data_button(
                            "Enable Service Accounts",
                            f"userset {user_id} rcedit {key}",
                            position="body",
                        )
                else:
                    buttons.data_button(
                        "Edit", f"userset {user_id} rcedit {key}", position="body"
                    )
            msg += "Click the button to edit."
            buttons.data_button("Back", f"userset {user_id} rclone", position="footer")
            buttons.data_button("Close", f"userset {user_id} close", position="footer")
        elif edit_type == "gdvar":
            if key == "setcred":
                if await aiopath.exists(f"tokens/{user_id}.pickle"):
                    buttons.data_button(
                        "Delete Token",
                        f"userset {user_id} gdedit_deltoken",
                        position="body",
                    )
                else:
                    buttons.data_button(
                        "Add Token",
                        f"userset {user_id} gdedit_addtoken",
                        position="body",
                    )
                if await aiopath.exists(f"tokens/{user_id}-accounts"):
                    buttons.data_button(
                        "Delete Credentials",
                        f"userset {user_id} gdedit_delcred",
                        position="body",
                    )
                else:
                    buttons.data_button(
                        "Add Credentials",
                        f"userset {user_id} gdedit_addcred",
                        position="body",
                    )
            else:
                gdrive_user_dict = user_dict.get("gdrive_user")
                value = (
                    str(gdrive_user_dict[key]) if str(gdrive_user_dict[key]) else "None"
                )
                msg = f"Edit <b>{key}</b> for {name}:\n"
                msg += f"Current value is <u>{value}</u>\n\n"
                if key == "team_drive":
                    if value == "True":
                        buttons.data_button(
                            "Switch to Personal Drive",
                            f"userset {user_id}  gdedit {key}",
                            position="body",
                        )
                    else:
                        buttons.data_button(
                            "Switch to Team Drive",
                            f"userset {user_id}  gdedit {key}",
                            position="body",
                        )
                elif key == "stop_duplicate":
                    if value == "True":
                        buttons.data_button(
                            "Disable Stop Duplicate",
                            f"userset {user_id} gdedit {key}",
                            position="body",
                        )
                    else:
                        buttons.data_button(
                            "Enable Stop Duplicate",
                            f"userset {user_id} gdedit {key}",
                            position="body",
                        )
                elif key == "service_accounts":
                    if not await aiopath.exists(f"tokens/{user_id}-accounts"):
                        msg += "<b>WARNING:</b> Gdrive Service Accounts is <b>Not Exists</b>\n"
                    if value == "True":
                        buttons.data_button(
                            "Disable Service Accounts",
                            f"userset {user_id} gdedit {key}",
                            position="body",
                        )
                    else:
                        buttons.data_button(
                            "Enable Service Accounts",
                            f"userset {user_id} gdedit {key}",
                            position="body",
                        )
                else:
                    buttons.data_button(
                        "Edit", f"userset {user_id} gdedit {key}", position="body"
                    )
            msg += "Click the button to edit."
            buttons.data_button("Back", f"userset {user_id} gdrive", position="footer")
            buttons.data_button("Close", f"userset {user_id} close", position="footer")
        elif edit_type == "psvar":
            upload_user_dict = user_dict.get("upload_user")
            path_shortcuts = upload_user_dict.get("path_shortcuts")
            value = str(path_shortcuts[key]) if str(path_shortcuts[key]) else "None"
            msg = f"Edit <b>{key}</b> for {name}:\n"
            msg += f"Current value is <u>{value}</u>\n\n"
            msg += "Click the button to edit."
            buttons.data_button(
                "Delete", f"userset {user_id} psdel {key}", position="body"
            )
            buttons.data_button(
                "Edit", f"userset {user_id} psedit {key}", position="body"
            )
            buttons.data_button(
                "Back", f"userset {user_id} pathshort", position="footer"
            )
            buttons.data_button("Close", f"userset {user_id} close", position="footer")
    return msg, buttons.build_menu(2, 6, 1, 2)


async def update_buttons(message, edit_type=None, key=None):
    from_user = message.from_user
    msg, button = await get_buttons(from_user, edit_type, key)
    await edit_message(message, msg, button)


async def edit_aria(key, value, query):
    user_id = query.from_user.id
    aria2_user_dict = user_data[user_id]["aria2_user"]
    if key == "ariavar_key":
        key, value = [x.strip() for x in value.split(":", 1)]
    if value.lower() == "true":
        value = "true"
    elif value.lower() == "false":
        value = "false"
    elif value.lower() == "none":
        value = ""
    aria2_user_dict.update({key: value})
    update_user_ldata(user_id, "aria2_user", aria2_user_dict)
    await database.update_user_data(user_id)
    await query.answer("Aria2 Config Updated", show_alert=True)


async def edit_upload(key, value, query):
    user_id = query.from_user.id
    upload_user_dict = user_data[user_id]["upload_user"]
    if key == "psvar_add":
        lines = value.split("\n")
        value = upload_user_dict["path_shortcuts"]
        key = "path_shortcuts"
        for line in lines:
            data = line.split(maxsplit=1)
            if len(data) != 2:
                await query.answer("Invalid Format", show_alert=True)
                return
            value.update({data[0]: data[1]})
    elif key == "psedit":
        key = "path_shortcuts"
        upload_user_dict["path_shortcuts"].update(value)
        value = upload_user_dict["path_shortcuts"]
    elif key == "psdel":
        key = "path_shortcuts"
        upload_user_dict["path_shortcuts"].pop(value)
        value = upload_user_dict["path_shortcuts"]
    elif key == "excluded_extensions":
        extensions = [ext.lstrip(".").lower() for ext in value.split() if ext]
        extensions.extend(["aria2", "!qB"])
        value = list(set(extensions))
    elif value.lower() == "none":
        value = ""
    upload_user_dict.update({key: value})
    update_user_ldata(user_id, "upload_user", upload_user_dict)
    await database.update_user_data(user_id)
    await query.answer("Upload Config Updated", show_alert=True)


async def edit_leech(key, value, query):
    user_id = query.from_user.id
    leech_user_dict = user_data[user_id]["leech_user"]
    if key == "split_size":
        if not value.isdigit():
            value = get_size_bytes(value)
        max_size = 4194304000 if IS_PREMIUM_USER else 2097152000
        value = min(max_size, max(52428800, int(value)))
    if value.lower() == "none":
        value = ""
    leech_user_dict.update({key: value})
    update_user_ldata(user_id, "leech_user", leech_user_dict)
    await database.update_user_data(user_id)
    await query.answer("Leech Config Updated", show_alert=True)


async def edit_rclone(key, value, query):
    user_id = query.from_user.id
    rclone_user_dict = user_data[user_id]["rclone_user"]
    if value.lower() == "none":
        value = ""
    rclone_user_dict.update({key: value})
    update_user_ldata(user_id, "rclone_user", rclone_user_dict)
    await database.update_user_data(user_id)
    await query.answer("Rclone Config Updated", show_alert=True)


async def conversation_handler(client, query, msg, document=False, photo=False):
    message = query.message
    from_user = query.from_user
    if document:
        filters = filters.document
    elif photo:
        filters = filters.photo
    else:
        filters = filters.text
    try:
        reply_text_message = await client.send_message(message.chat.id, msg)
        response_message = await client.listen(
            chat_id=message.chat.id,
            user_id=from_user.id,
            filters=filters,
            timeout=60,
        )
    except ListenerTimeout:
        await query.answer("Listener Timeout", show_alert=True)
        await auto_delete_message(client, reply_text_message, 0)
        return
    except ListenerStopped:
        await query.answer()
        await auto_delete_message(client, reply_text_message, 0)
        return
    await auto_delete_message(client, [reply_text_message, response_message], 0)
    return response_message


@new_task
async def edit_user_settings(client, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]) and user_id != OWNER_ID:
        await query.answer("You are not allowed to do this", show_alert=True)
        return
    await client.stop_listening(
        chat_id=message.chat.id,
        user_id=user_id,
    )
    if data[2] == "close":
        await query.answer()
        await auto_delete_message(client, [message, message.reply_to_message], 0)
    elif data[2] == "back":
        await query.answer()
        await update_buttons(query)
    elif data[2] in [
        "aria",
        "yt-dlp",
        "upload",
        "leech",
        "rclone",
        "gdrive",
        "pathshort",
    ]:
        await query.answer()
        await update_buttons(query, data[2])
    elif data[2] == "ariavar_reset":
        update_user_ldata(user_id, "aria2_user", None)
        await database.update_user_data(user_id)
        await query.answer("Aria2 Config Resetted", show_alert=True)
        await update_buttons(query, "aria")
    elif data[2] == "ariavar_key":
        msg = "Send the key and value separated by colon.\n"
        msg += "<b>Example:</b> key:value\n"
        msg += "<b>Timeout:</b> 60s"
        response_message = await conversation_handler(client, query, msg)
        if response_message is None:
            return
        await edit_aria("ariavar_key", response_message.text, query)
        await update_buttons(query, "aria")
    elif data[2] == "lhvar_reset":
        update_user_ldata(user_id, "leech_user", None)
        await database.update_user_data(user_id)
        await query.answer("Leech Config Resetted", show_alert=True)
        await update_buttons(query, "leech")
    elif data[2] == "psvar_add":
        msg = "Send path name as a shortcut and the path/id seperated by space.\n"
        msg += "Multiple names and paths separated by new line"
        msg += "<b>Example:</b>\n"
        msg += "<code>name1 path1\nname2 path2</code>\n"
        msg += "<b>Timeout:</b> 60s"
        response_message = await conversation_handler(client, query, msg)
        if response_message is None:
            return
        await edit_upload("psvar_add", response_message.text, query)
        await update_buttons(query, "pathshort")
    elif data[2] in ["ariavar", "ytvar", "upvar", "lhvar", "rcvar", "gdvar", "psvar"]:
        await query.answer()
        await update_buttons(query, data[2], data[3])
    elif data[2] == "ariaedit":
        msg = f"Send the new value for {data[3]}.\n"
        msg += "<b>Timeout:</b> 60s"
        response_message = await conversation_handler(client, query, msg)
        if response_message is None:
            return
        await edit_aria(data[3], response_message.text, query)
        await update_buttons(query, "ariavar", data[3])
    elif data[2] == "ytedit":
        msg = "Send YT-DLP option.\n"
        msg += "<b>Format</b>: key:value|key:value|key:value.\n"
        msg += (
            "<b>Example</b>: format:bv*+mergeall[vcodec=none]|nocheckcertificate:True\n"
        )
        msg += "<b>Timeout</b>: 60s."
        msg += "<b>NOTE</b>: Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a>"
        response_message = await conversation_handler(client, query, msg)
        if response_message is None:
            return
        update_user_ldata(user_id, "yt_user", response_message.text)
        await database.update_user_data(user_id)
        await query.answer("YT-DLP Options Updated", show_alert=True)
        await update_buttons(query, "yt-dlp")
    elif data[2] == "upedit":
        upload_user_dict = user_data[user_id]["upload_user"]
        if data[3] == "upload_type":
            value = (
                "Gdrive"
                if upload_user_dict.get("upload_type") == "Rclone"
                else "Rclone"
            )
            msg = ""
        elif data[3] == "excluded_extensions":
            msg = (
                "Send exluded extenions seperated by space without dot at beginning.\n"
            )
            msg += "<b>Example</b>: exe html url\n"
            msg += "<b>Timeout</b>: 60s."
        elif data[3] == "name_sub":
            msg = "Send file name character substitution rule.\n"
            msg += "<b>Example</b>: script/code/s | mirror/leech | tea/ /s | clone | cpu/ | \[mltb\]/mltb | \\text\\/text/s\n"
            msg += "1. script will get replaced by code with sensitive case\n"
            msg += "2. mirror will get replaced by leech\n"
            msg += "3. tea will get replaced by space with sensitive case\n"
            msg += "4. clone will get removed\n"
            msg += "5. cpu will get replaced by space\n"
            msg += "6. [mltb] will get replaced by mltb\n"
            msg += "7. \\text\\ will get replaced by text with sensitive case\n"
            msg += "<b>NOTE</b>: You must add \ before any character, those are the characters: \^$.|?*+()[]{}-\n"
            msg += "<b>Timeout</b>: 60s."
        else:
            msg = f"Send the new value for {data[3]}.\n"
            msg += "<b>Timeout:</b> 60s"
        if msg:
            response_message = await conversation_handler(client, query, msg)
            if response_message is None:
                return
            value = response_message.text
        await edit_upload(data[3], value, query)
        await update_buttons(query, "upvar", data[3])
    elif data[2] == "lhedit":
        leech_user_dict = user_data[user_id]["leech_user"]
        if data[3] == "leech_type":
            value = (
                "Document" if leech_user_dict.get("leech_type") == "Media" else "Media"
            )
        elif data[3] == "leech_method":
            value = "Bot" if leech_user_dict.get("leech_method") == "User" else "User"
        elif data[3] in ["equal_splits", "media_group", "mixed_leech"]:
            value = not leech_user_dict.get(data[3])
        elif data[3] in ["split_size", "leech_dest", "leech_prefix", "thumb_layout"]:
            if data[3] == "split_size":
                msg = "Send Leech split size in bytes.\n<b>Example</b>: 104857600(100MB)\n"
                msg += "<b>MaxSize</b>: 2097152000(FreeUser), 4194304000(PremiumUser)\n<b>Timeout</b>: 60s."
            elif data[3] == "leech_dest":
                msg = "Send leech destination ID/USERNAME/PM.\n<b>Timeout</b>: 60s."
            elif data[3] == "leech_prefix":
                msg = "Send Leech Filename Prefix. You can add HTML tags.\nTimeout</b>: 60s."
            elif data[3] == "thumb_layout":
                msg = "Send thumbnail layout (width x height, 2x2, 3x2, etc).\n<b>Timeout</b>: 60s."
            response_message = await conversation_handler(client, query, msg)
            if response_message is None:
                return
            value = response_message.text
        elif data[3] == "custom_thumb":
            if leech_user_dict.get("custom_thumb") == "Not Exists":
                msg = "Send the new thumbnail for custom thumb.\n"
                msg += "<b>Timeout:</b> 60s"
                response_message = await conversation_handler(
                    client, query, msg, photo=True
                )
                if response_message is None:
                    return
                file_path = f"Thumbnails/{user_id}.jpg"
                photo_dir = await response_message.download()
                await sync_to_async(
                    Image.open(photo_dir).convert("RGB").save, file_path, "JPEG"
                )
                await remove(photo_dir)
                value = file_path
            else:
                file_path = leech_user_dict["custom_thumb"]
                await remove(file_path)
                value = "Not Exists"
            await database.update_user_doc(user_id, file_path)
        await edit_leech(data[3], value, query)
        await update_buttons(query, "lhvar", data[3])
    elif data[2] == "rcedit":
        rclone_user_dict = user_data[user_id]["rclone_user"]
        if data[3] == "gdrive_sa":
            value = not rclone_user_dict.get("gdrive_sa")
        else:
            msg = f"Send the new value for {data[3]}.\n"
            msg += "<b>Timeout:</b> 60s"
            response_message = await conversation_handler(client, query, msg)
            if response_message is None:
                return
            value = response_message.text
        await edit_rclone(data[3], value, query)
        await update_buttons(query, "rcvar", data[3])
    elif data[2] == "rcedit_remote":
        rclone_user_dict = user_data[user_id]["rclone_user"]
        if rclone_user_dict["remote"] == data[3]:
            await query.answer("Already Selected", show_alert=True)
        else:
            value = data[3]
            await edit_rclone("remote", value, query)
            await update_buttons(query, "rcvar", "remote")
        return
    elif data[2] == "rcedit_add":
        msg = "Send the Rclone Config file to add.\n<b>NOTE:</b> The file should be in .ini format.\n"
        msg += "<b>Timeout:</b> 60s"
        response_message = await conversation_handler(client, query, msg, document=True)
        if response_message is None:
            return
        file_path = f"rclone/{user_id}.conf"
        await response_message.download(file_path)
        try:
            config = ConfigParser()
            config.read(file_path)
            if user_id != OWNER_ID:
                local_storage = [
                    x
                    for x in config.sections()
                    if config.get(x, "type", fallback="local") in ["local", "alias"]
                ]
                if local_storage:
                    raise PermissionError("Not allowed")
        except Exception as e:
            await remove(file_path)
            if "Not allowed" in str(e):
                await query.answer("Local Storage is not allowed", show_alert=True)
                LOGGER.error("Rclone Config Error: Local Storage is not allowed")
            else:
                await query.answer("Invalid Config File", show_alert=True)
                LOGGER.error(f"Rclone Config Error: {e}")
            return
        await query.answer("Rclone Config Added", show_alert=True)
        await database.update_user_doc(user_id, file_path)
        await update_buttons(query, "rcvar", "setconf")
    elif data[2] == "rcedit_del":
        file_path = f"rclone/{user_id}.conf"
        await remove(file_path)
        await query.answer("Rclone Config Deleted", show_alert=True)
        await database.update_user_doc(user_id, file_path)
        await update_buttons(query, "rcvar", "setconf")
    elif data[2] == "gdedit":
        gdrive_user_dict = user_data[user_id]["gdrive_user"]
        if data[3] == "team_drive":
            value = not gdrive_user_dict.get("team_drive")
        elif data[3] == "stop_duplicate":
            value = not gdrive_user_dict.get("stop_duplicate")
        elif data[3] == "service_accounts":
            value = not gdrive_user_dict.get("service_accounts")
        else:
            msg = f"Send the new value for {data[3]}.\n"
            msg += "<b>Timeout:</b> 60s"
            response_message = await conversation_handler(client, query, msg)
            if response_message is None:
                return
            value = response_message.text
        gdrive_user_dict[data[3]] = value
        update_user_ldata(user_id, "gdrive_user", gdrive_user_dict)
        await database.update_user_data(user_id)
        await query.answer("Gdrive Config Updated", show_alert=True)
        await update_buttons(query, "gdvar", data[3])
    elif data[2] == "gdedit_addtoken":
        msg = "Send the Gdrive Token file to add.\n<b>NOTE:</b> The file should be in .pickle format.\n"
        msg += "<b>Timeout:</b> 60s"
        response_message = await conversation_handler(client, query, msg, document=True)
        if response_message is None:
            return
        file_path = f"tokens/{user_id}.pickle"
        await response_message.download(file_path)
        await query.answer("Gdrive Token Added", show_alert=True)
        await database.update_user_doc(user_id, file_path)
        await update_buttons(query, "gdvar", "setcred")
    elif data[2] == "gdedit_deltoken":
        file_path = f"tokens/{user_id}.pickle"
        await remove(file_path)
        await query.answer("Gdrive Token Deleted", show_alert=True)
        await database.update_user_doc(user_id, file_path)
        await update_buttons(query, "gdvar", "setcred")
    elif data[2] == "gdedit_addcred":
        msg = "Send the Gdrive Credentials files as a zip file to add.\n<b>NOTE:</b> The file should be in .json format.\n"
        msg += "<b>Timeout:</b> 60s"
        response_message = await conversation_handler(client, query, msg, document=True)
        if response_message is None:
            return
        file_path = f"tokens/{user_id}-accounts.zip"
        await response_message.download(file_path)
        await create_subprocess_exec("7z", "x", file_path, f"-o{user_id}-accounts")
        await database.update_user_doc(user_id, file_path)
        await remove(file_path)
        await query.answer("Gdrive Credentials Added", show_alert=True)
        await update_buttons(query, "gdvar", "setcred")
    elif data[2] == "gdedit_delcred":
        file_path = f"tokens/{user_id}-accounts"
        await aiormtree(file_path)
        await query.answer("Gdrive Credentials Deleted", show_alert=True)
        await database.update_user_doc(user_id, file_path)
        await update_buttons(query, "gdvar", "setcred")
    elif data[2] == "psedit":
        upload_user_dict = user_data[user_id]["upload_user"]
        msg = f"Send the new value for {data[3]}.\n"
        msg += "<b>Timeout:</b> 60s"
        response_message = await conversation_handler(client, query, msg)
        if response_message is None:
            return
        value = {data[3]: response_message.text}
        await edit_upload("psedit", value, query)
        await update_buttons(query, "psvar", data[3])
    elif data[2] == "psdel":
        value = data[3]
        await edit_upload("psdel", value, query)
        await update_buttons(query, "pathshort")


@new_task
async def user_settings(_, message):
    from_user = message.from_user
    msg, button = await get_buttons(from_user)
    await send_message(message, msg, button)


bot.add_handler(
    MessageHandler(
        user_settings,
        filters=filters.command(BotCommands.UserSetCommand, case_sensitive=True)
        & CustomFilters.authorized,
    )
)
bot.add_handler(
    CallbackQueryHandler(edit_user_settings, filters=filters.regex("^userset"))
)
