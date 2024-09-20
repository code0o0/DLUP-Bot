from aiofiles.os import remove, path as aiopath, makedirs
from html import escape
from io import BytesIO
from os import getcwd
from pyrogram import filters
from pyrogram.errors import ListenerTimeout, ListenerStopped
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import (
    bot,
    IS_PREMIUM_USER,
    user_data,
    config_dict,
    OWNER_ID,
    MAX_SPLIT_SIZE,
    global_extension_filter,
)
from ..helper.ext_utils.bot_utils import (
    update_user_ldata,
    new_task,
    get_size_bytes,
)
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.media_utils import create_thumb
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    send_message,
    edit_message,
    send_file,
    delete_message,
)


async def get_user_settings(from_user):
    user_id = from_user.id
    name = from_user.mention
    buttons = ButtonMaker()
    thumbpath = f"Thumbnails/{user_id}.jpg"
    rclone_conf = f"rclone/{user_id}.conf"
    token_pickle = f"tokens/{user_id}.pickle"
    user_dict = user_data.get(user_id, {})

    if (
        user_dict.get("as_doc", False)
        or "as_doc" not in user_dict
        and config_dict["AS_DOCUMENT"]
    ):
        ltype = "DOCUMENT"
    else:
        ltype = "MEDIA"

    thumbmsg = "Exists" if await aiopath.exists(thumbpath) else "Not Exists"

    if user_dict.get("split_size", False):
        split_size = user_dict["split_size"]
    else:
        split_size = config_dict["LEECH_SPLIT_SIZE"]

    if (
        user_dict.get("equal_splits", False)
        or "equal_splits" not in user_dict
        and config_dict["EQUAL_SPLITS"]
    ):
        equal_splits = "Enabled"
    else:
        equal_splits = "Disabled"

    if (
        user_dict.get("media_group", False)
        or "media_group" not in user_dict
        and config_dict["MEDIA_GROUP"]
    ):
        media_group = "Enabled"
    else:
        media_group = "Disabled"

    if user_dict.get("lprefix", False):
        lprefix = user_dict["lprefix"]
    elif "lprefix" not in user_dict and config_dict["LEECH_FILENAME_PREFIX"]:
        lprefix = config_dict["LEECH_FILENAME_PREFIX"]
    else:
        lprefix = "None"

    if user_dict.get("leech_dest", False):
        leech_dest = user_dict["leech_dest"]
    elif "leech_dest" not in user_dict and config_dict["LEECH_DUMP_CHAT"]:
        leech_dest = config_dict["LEECH_DUMP_CHAT"]
    else:
        leech_dest = "None"

    if (
        IS_PREMIUM_USER
        and user_dict.get("user_transmission", False)
        or "user_transmission" not in user_dict
        and config_dict["USER_TRANSMISSION"]
    ):
        leech_method = "user"
    else:
        leech_method = "bot"
    if (
        IS_PREMIUM_USER
        and user_dict.get("mixed_leech", False)
        or "mixed_leech" not in user_dict
        and config_dict["MIXED_LEECH"]
    ):
        mixed_leech = "Enabled"
    else:
        mixed_leech = "Disabled"
    
    if user_dict.get("thumb_layout", False):
        thumb_layout = user_dict["thumb_layout"]
    elif "thumb_layout" not in user_dict and config_dict["THUMBNAIL_LAYOUT"]:
        thumb_layout = config_dict["THUMBNAIL_LAYOUT"]
    else:
        thumb_layout = "None"
        
    buttons.data_button("Leech", f"userset {user_id} leech", position="header")
    buttons.data_button("Rclone", f"userset {user_id} rclone", position="header")
    rccmsg = "Exists" if await aiopath.exists(rclone_conf) else "Not Exists"
    if user_dict.get("rclone_path", False):
        rccpath = user_dict["rclone_path"]
    elif RP := config_dict["RCLONE_PATH"]:
        rccpath = RP
    else:
        rccpath = "None"

    buttons.data_button("Gdrive Tools", f"userset {user_id} gdrive", position="header")
    tokenmsg = "Exists" if await aiopath.exists(token_pickle) else "Not Exists"
    if user_dict.get("gdrive_id", False):
        gdrive_id = user_dict["gdrive_id"]
    elif GI := config_dict["GDRIVE_ID"]:
        gdrive_id = GI
    else:
        gdrive_id = "None"
    index = user_dict["index_url"] if user_dict.get("index_url", False) else "None"
    if (
        user_dict.get("stop_duplicate", False)
        or "stop_duplicate" not in user_dict
        and config_dict["STOP_DUPLICATE"]
    ):
        sd_msg = "Enabled"
    else:
        sd_msg = "Disabled"

    upload_paths = "Added" if user_dict.get("upload_paths", False) else "None"
    buttons.data_button("Upload Paths", f"userset {user_id} upload_paths", position="header")

    default_upload = (
        user_dict.get("default_upload", "") or config_dict["DEFAULT_UPLOAD"]
    )
    du = "Gdrive API" if default_upload == "gd" else "Rclone"
    dub = "Gdrive API" if default_upload != "gd" else "Rclone"
    buttons.data_button(f"Upload using {dub}", f"userset {user_id} {default_upload}", position="header")

    buttons.data_button("Excluded Extensions", f"userset {user_id} ex_ex", position="header")
    if user_dict.get("excluded_extensions", False):
        ex_ex = user_dict["excluded_extensions"]
    elif "excluded_extensions" not in user_dict and global_extension_filter:
        ex_ex = global_extension_filter
    else:
        ex_ex = "None"
    
    ns_msg = "Added" if user_dict.get("name_sub", False) else "None"
    buttons.data_button("Name Substitute", f"userset {user_id} name_substitute", position="header")

    buttons.data_button("YT-DLP Options", f"userset {user_id} yto", position="header")
    if user_dict.get("yt_opt", False):
        ytopt = user_dict["yt_opt"]
    elif "yt_opt" not in user_dict and (YTO := config_dict["YT_DLP_OPTIONS"]):
        ytopt = YTO
    else:
        ytopt = "None"

    if user_dict:
        buttons.data_button("Reset All", f"userset {user_id} reset")
    buttons.data_button("Close", f"userset {user_id} close", position="footer")

    text = f"""<u>Settings for {name}</u>
Leech Type is <b>{ltype}</b>
Custom Thumbnail <b>{thumbmsg}</b>
Leech Split Size is <b>{split_size}</b>
Equal Splits is <b>{equal_splits}</b>
Media Group is <b>{media_group}</b>
Leech Prefix is <code>{escape(lprefix)}</code>
Leech Destination is <code>{leech_dest}</code>
Leech by <b>{leech_method}</b> session
Mixed Leech is <b>{mixed_leech}</b>
Thumbnail Layout is <b>{thumb_layout}</b>
Rclone Config <b>{rccmsg}</b>
Rclone Path is <code>{rccpath}</code>
Gdrive Token <b>{tokenmsg}</b>
Upload Paths is <b>{upload_paths}</b>
Gdrive ID is <code>{gdrive_id}</code>
Index Link is <code>{index}</code>
Stop Duplicate is <b>{sd_msg}</b>
Default Upload is <b>{du}</b>
Name substitution is <b>{ns_msg}</b>
Excluded Extensions is <code>{ex_ex}</code>
YT-DLP Options is <b><code>{escape(ytopt)}</code></b>"""

    return text, buttons.build_menu(2, 2)

async def update_user_settings(query):
    msg, button = await get_user_settings(query.from_user)
    await edit_message(query.message, msg, button)

@new_task
async def user_settings(client, message):
    from_user = message.from_user
    msg, button = await get_user_settings(from_user)
    await send_message(message, msg, button)

async def set_thumb(message):
    user_id = message.from_user.id
    des_dir = await create_thumb(message, user_id)
    update_user_ldata(user_id, "thumb", des_dir)
    await delete_message(message)
    if config_dict["DATABASE_URL"]:
        await database.update_user_doc(user_id, des_dir)

async def add_rclone(message):
    user_id = message.from_user.id
    rpath = f"{getcwd()}/rclone/"
    await makedirs(rpath, exist_ok=True)
    des_dir = f"{rpath}{user_id}.conf"
    await message.download(file_name=des_dir)
    update_user_ldata(user_id, "rclone_config", f"rclone/{user_id}.conf")
    await delete_message(message)
    if config_dict["DATABASE_URL"]:
        await database.update_user_doc(user_id, des_dir)

async def add_token_pickle(message):
    user_id = message.from_user.id
    tpath = f"{getcwd()}/tokens/"
    await makedirs(tpath, exist_ok=True)
    des_dir = f"{tpath}{user_id}.pickle"
    await message.download(file_name=des_dir)
    update_user_ldata(user_id, "token_pickle", f"tokens/{user_id}.pickle")
    await delete_message(message)
    if config_dict["DATABASE_URL"]:
        await database.update_user_doc(user_id, des_dir)

async def delete_path(message):
    user_id = message.from_user.id
    user_dict = user_data.get(user_id, {})
    names = message.text.split()
    for name in names:
        if name in user_dict["upload_paths"]:
            del user_dict["upload_paths"][name]
    new_value = user_dict["upload_paths"]
    update_user_ldata(user_id, "upload_paths", new_value)
    await delete_message(message)
    if config_dict["DATABASE_URL"]:
        await database.update_user_doc(user_id, new_value)

async def set_option(message, option):
    user_id = message.from_user.id
    value = message.text
    if option == "split_size":
        if not value.isdigit():
            value = get_size_bytes(value)
        value = min(int(value), MAX_SPLIT_SIZE)
    elif option == "excluded_extensions":
        fx = value.split()
        value = ["aria2", "!qB"]
        for x in fx:
            x = x.lstrip(".")
            value.append(x.strip().lower())
    elif option == "upload_paths":
        user_dict = user_data.get(user_id, {})
        user_dict.setdefault("upload_paths", {})
        lines = value.split("/n")
        for line in lines:
            data = line.split(maxsplit=1)
            if len(data) != 2:
                await send_message(message, "Wrong format! Add <name> <path>")
                return
            name, path = data
            user_dict["upload_paths"][name] = path
        value = user_dict["upload_paths"]
    update_user_ldata(user_id, option, value)
    await delete_message(message)
    if config_dict["DATABASE_URL"]:
        await database.update_user_data(user_id)

async def conversation_handler(client, query, photo=False, document=False):
    if photo:
        event_filter = filters.photo
    elif document:
        event_filter = filters.document
    else:
        event_filter = filters.regex(r'^[^/]')
    message = query.message
    from_user = query.from_user
    try:
        response_message = await client.listen(
            chat_id=message.chat.id,
            user_id=from_user.id,
            filters=event_filter,
            timeout=30,
            )
    except ListenerTimeout:
        await update_user_settings(query)
        return
    except ListenerStopped:
        return
    return response_message

@new_task
async def edit_user_settings(client, query):
    from_user = query.from_user
    user_id = from_user.id
    name = from_user.mention
    message = query.message
    data = query.data.split()
    thumb_path = f"Thumbnails/{user_id}.jpg"
    rclone_conf = f"rclone/{user_id}.conf"
    token_pickle = f"tokens/{user_id}.pickle"
    user_dict = user_data.get(user_id, {})
    if user_id != int(data[1]) and user_id != OWNER_ID:
        await query.answer("Not Yours!", show_alert=True)
    await client.stop_listening(
        chat_id=message.chat.id,
        user_id=user_id,
        )
    if data[2] in [
        "as_doc",
        "equal_splits",
        "media_group",
        "user_transmission",
        "stop_duplicate",
        "mixed_leech",
    ]:
        update_user_ldata(user_id, data[2], data[3] == "true")
        await query.answer()
        await update_user_settings(query)
        if config_dict["DATABASE_URL"]:
            await database.update_user_data(user_id)
    elif data[2] in ["thumb", "rclone_config", "token_pickle"]:
        if data[2] == "thumb":
            fpath = thumb_path
        elif data[2] == "rclone_config":
            fpath = rclone_conf
        else:
            fpath = token_pickle
        if await aiopath.exists(fpath):
            await query.answer()
            await remove(fpath)
            update_user_ldata(user_id, data[2], "")
            await update_user_settings(query)
            if config_dict["DATABASE_URL"]:
                await database.update_user_doc(user_id, data[2])
        else:
            await query.answer("Old Settings", show_alert=True)
            await update_user_settings(query)
    elif data[2] in [
        "yt_opt",
        "lprefix",
        "index_url",
        "excluded_extensions",
        "name_sub",
        "thumb_layout",
    ]:
        await query.answer()
        update_user_ldata(user_id, data[2], "")
        await update_user_settings(query)
        if config_dict["DATABASE_URL"]:
            await database.update_user_data(user_id)
    elif data[2] in ["split_size", "leech_dest", "rclone_path", "gdrive_id"]:
        await query.answer()
        if data[2] in user_data.get(user_id, {}):
            del user_data[user_id][data[2]]
            await update_user_settings(query)
            if config_dict["DATABASE_URL"]:
                await database.update_user_data(user_id)
    elif data[2] == "leech":
        await query.answer()
        thumbpath = f"Thumbnails/{user_id}.jpg"
        buttons = ButtonMaker()
        buttons.data_button("Thumbnail", f"userset {user_id} sthumb", position="header")
        thumbmsg = "Exists" if await aiopath.exists(thumbpath) else "Not Exists"
        buttons.data_button("Leech Split Size", f"userset {user_id} lss", position="header")
        if user_dict.get("split_size", False):
            split_size = user_dict["split_size"]
        else:
            split_size = config_dict["LEECH_SPLIT_SIZE"]
        buttons.data_button("Leech Destination", f"userset {user_id} ldest", position="header")
        if user_dict.get("leech_dest", False):
            leech_dest = user_dict["leech_dest"]
        elif "leech_dest" not in user_dict and config_dict["LEECH_DUMP_CHAT"]:
            leech_dest = config_dict["LEECH_DUMP_CHAT"]
        else:
            leech_dest = "None"
        buttons.data_button("Leech Prefix", f"userset {user_id} leech_prefix", position="header")
        if user_dict.get("lprefix", False):
            lprefix = user_dict["lprefix"]
        elif "lprefix" not in user_dict and config_dict["LEECH_FILENAME_PREFIX"]:
            lprefix = config_dict["LEECH_FILENAME_PREFIX"]
        else:
            lprefix = "None"
        if (
            user_dict.get("as_doc", False)
            or "as_doc" not in user_dict
            and config_dict["AS_DOCUMENT"]
        ):
            ltype = "DOCUMENT"
            buttons.data_button("Send As Media", f"userset {user_id} as_doc false", position="header")
        else:
            ltype = "MEDIA"
            buttons.data_button("Send As Document", f"userset {user_id} as_doc true", position="header")
        if (
            user_dict.get("equal_splits", False)
            or "equal_splits" not in user_dict
            and config_dict["EQUAL_SPLITS"]
        ):
            buttons.data_button(
                "Disable Equal Splits", f"userset {user_id} equal_splits false", position="header"
            )
            equal_splits = "Enabled"
        else:
            buttons.data_button(
                "Enable Equal Splits", f"userset {user_id} equal_splits true", position="header"
            )
            equal_splits = "Disabled"
        if (
            user_dict.get("media_group", False)
            or "media_group" not in user_dict
            and config_dict["MEDIA_GROUP"]
        ):
            buttons.data_button(
                "Disable Media Group", f"userset {user_id} media_group false", position="header"
            )
            media_group = "Enabled"
        else:
            buttons.data_button(
                "Enable Media Group", f"userset {user_id} media_group true", position="header"
            )
            media_group = "Disabled"
        if (
            IS_PREMIUM_USER
            and user_dict.get("user_transmission", False)
            or "user_transmission" not in user_dict
            and config_dict["USER_TRANSMISSION"]
        ):
            buttons.data_button(
                "Leech by Bot", f"userset {user_id} user_transmission false", position="header"
            )
            leech_method = "user"
        elif IS_PREMIUM_USER:
            leech_method = "bot"
            buttons.data_button(
                "Leech by User", f"userset {user_id} user_transmission true", position="header"
            )
        else:
            leech_method = "bot"

        if (
            IS_PREMIUM_USER
            and user_dict.get("mixed_leech", False)
            or "mixed_leech" not in user_dict
            and config_dict["MIXED_LEECH"]
        ):
            mixed_leech = "Enabled"
            buttons.data_button(
                "Disable Mixed Leech", f"userset {user_id} mixed_leech false", position="header"
            )
        elif IS_PREMIUM_USER:
            mixed_leech = "Disabled"
            buttons.data_button(
                "Enable Mixed Leech", f"userset {user_id} mixed_leech true", position="header"
            )
        else:
            mixed_leech = "Disabled"

        buttons.data_button("Thumbnail Layout", f"userset {user_id} tlayout", position="header")
        if user_dict.get("thumb_layout", False):
            thumb_layout = user_dict["thumb_layout"]
        elif "thumb_layout" not in user_dict and config_dict["THUMBNAIL_LAYOUT"]:
            thumb_layout = config_dict["THUMBNAIL_LAYOUT"]
        else:
            thumb_layout = "None"

        buttons.data_button("Back", f"userset {user_id} back")
        buttons.data_button("Close", f"userset {user_id} close")
        text = f"""<u>Leech Settings for {name}</u>
Leech Type is <b>{ltype}</b>
Custom Thumbnail <b>{thumbmsg}</b>
Leech Split Size is <b>{split_size}</b>
Equal Splits is <b>{equal_splits}</b>
Media Group is <b>{media_group}</b>
Leech Prefix is <code>{escape(lprefix)}</code>
Leech Destination is <code>{leech_dest}</code>
Leech by <b>{leech_method}</b> session
Mixed Leech is <b>{mixed_leech}</b>
Thumbnail Layout is <b>{thumb_layout}</b>
"""
        await edit_message(message, text, buttons.build_menu(2, 2))
    elif data[2] == "rclone":
        await query.answer()
        buttons = ButtonMaker()
        buttons.data_button("Rclone Config", f"userset {user_id} rcc", position="header")
        buttons.data_button("Default Rclone Path", f"userset {user_id} rcp", position="header")
        buttons.data_button("Back", f"userset {user_id} back")
        buttons.data_button("Close", f"userset {user_id} close")
        rccmsg = "Exists" if await aiopath.exists(rclone_conf) else "Not Exists"
        if user_dict.get("rclone_path", False):
            rccpath = user_dict["rclone_path"]
        elif RP := config_dict["RCLONE_PATH"]:
            rccpath = RP
        else:
            rccpath = "None"
        text = f"""<u>Rclone Settings for {name}</u>
Rclone Config <b>{rccmsg}</b>
Rclone Path is <code>{rccpath}</code>"""
        await edit_message(message, text, buttons.build_menu(2, 2))
    elif data[2] == "gdrive":
        await query.answer()
        buttons = ButtonMaker()
        buttons.data_button("token.pickle", f"userset {user_id} token", position="header")
        buttons.data_button("Default Gdrive ID", f"userset {user_id} gdid", position="header")
        buttons.data_button("Index URL", f"userset {user_id} index", position="header")
        if (
            user_dict.get("stop_duplicate", False)
            or "stop_duplicate" not in user_dict
            and config_dict["STOP_DUPLICATE"]
        ):
            buttons.data_button(
                "Disable Stop Duplicate", f"userset {user_id} stop_duplicate false", position="header"
            )
            sd_msg = "Enabled"
        else:
            buttons.data_button(
                "Enable Stop Duplicate", f"userset {user_id} stop_duplicate true", position="header"
            )
            sd_msg = "Disabled"
        buttons.data_button("Back", f"userset {user_id} back")
        buttons.data_button("Close", f"userset {user_id} close")
        tokenmsg = "Exists" if await aiopath.exists(token_pickle) else "Not Exists"
        if user_dict.get("gdrive_id", False):
            gdrive_id = user_dict["gdrive_id"]
        elif GDID := config_dict["GDRIVE_ID"]:
            gdrive_id = GDID
        else:
            gdrive_id = "None"
        index = user_dict["index_url"] if user_dict.get("index_url", False) else "None"
        text = f"""<u>Gdrive Tools Settings for {name}</u>
Gdrive Token <b>{tokenmsg}</b>
Gdrive ID is <code>{gdrive_id}</code>
Index URL is <code>{index}</code>
Stop Duplicate is <b>{sd_msg}</b>"""
        await edit_message(message, text, buttons.build_menu(2, 2))
    elif data[2] == "vthumb":
        await query.answer()
        await send_file(message, thumb_path, name)
        await update_user_settings(query)
    elif data[2] == "sthumb":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(thumb_path):
            buttons.data_button("View Thumbnail", f"userset {user_id} vthumb", position="header")
            buttons.data_button("Delete Thumbnail", f"userset {user_id} thumb", position="header")
        buttons.data_button("Back", f"userset {user_id} leech")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send a photo to save it as custom thumbnail. Timeout: 60 sec",
            buttons.build_menu(2, 2),
        )
        event = await conversation_handler(client, query, True)
        if event:
            await set_thumb(event)
            await update_user_settings(query)
    elif data[2] == "yto":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("yt_opt", False) or config_dict["YT_DLP_OPTIONS"]:
            buttons.data_button(
                "Remove YT-DLP Options", f"userset {user_id} yt_opt", position="header"
            )
        buttons.data_button("Back", f"userset {user_id} back")
        buttons.data_button("Close", f"userset {user_id} close")
        rmsg = """
Send YT-DLP Options. Timeout: 60 sec
Format: key:value|key:value|key:value.
Example: format:bv*+mergeall[vcodec=none]|nocheckcertificate:True
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.
        """
        await edit_message(message, rmsg, buttons.build_menu(2, 2))
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "yt_opt")
            await update_user_settings(query)
    elif data[2] == "lss":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("split_size", False):
            buttons.data_button("Reset Split Size", f"userset {user_id} split_size", position="header")
        buttons.data_button("Back", f"userset {user_id} leech")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message,
            f"Send Leech split size in bytes. IS_PREMIUM_USER: {IS_PREMIUM_USER}. Timeout: 60 sec",
            buttons.build_menu(2, 2),
        )
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "split_size")
            await update_user_settings(query)
    elif data[2] == "rcc":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(rclone_conf):
            buttons.data_button("Delete rclone.conf", f"userset {user_id} rclone_config", position="header")
        buttons.data_button("Back", f"userset {user_id} rclone")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message, "Send rclone.conf. Timeout: 60 sec", buttons.build_menu(2, 2)
        )
        event = await conversation_handler(client, query, document=True)
        if event:
            await add_rclone(event)
            await update_user_settings(query)
    elif data[2] == "rcp":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("rclone_path", False):
            buttons.data_button("Reset Rclone Path", f"userset {user_id} rclone_path", position="header")
        buttons.data_button("Back", f"userset {user_id} rclone")
        buttons.data_button("Close", f"userset {user_id} close")
        rmsg = "Send Rclone Path. Timeout: 60 sec"
        await edit_message(message, rmsg, buttons.build_menu(2, 2))
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "rclone_path")
            await update_user_settings(query)
    elif data[2] == "token":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(token_pickle):
            buttons.data_button("Delete token.pickle", f"userset {user_id} token_pickle", position="header")
        buttons.data_button("Back", f"userset {user_id} gdrive")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message, "Send token.pickle. Timeout: 60 sec", buttons.build_menu(2, 2)
        )
        event = await conversation_handler(client, query, document=True)
        if event:
            await add_token_pickle(event)
            await update_user_settings(query)
    elif data[2] == "gdid":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("gdrive_id", False):
            buttons.data_button("Reset Gdrive ID", f"userset {user_id} gdrive_id", position="header")
        buttons.data_button("Back", f"userset {user_id} gdrive")
        buttons.data_button("Close", f"userset {user_id} close")
        rmsg = "Send Gdrive ID. Timeout: 60 sec"
        await edit_message(message, rmsg, buttons.build_menu(2, 2))
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "gdrive_id")
            await update_user_settings(query)
    elif data[2] == "index":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("index_url", False):
            buttons.data_button("Remove Index URL", f"userset {user_id} index_url", position="header")
        buttons.data_button("Back", f"userset {user_id} gdrive")
        buttons.data_button("Close", f"userset {user_id} close")
        rmsg = "Send Index URL. Timeout: 60 sec"
        await edit_message(message, rmsg, buttons.build_menu(2, 2))
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "index_url")
            await update_user_settings(query)
    elif data[2] == "leech_prefix":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get("lprefix", False)
            or "lprefix" not in user_dict
            and config_dict["LEECH_FILENAME_PREFIX"]
        ):
            buttons.data_button("Remove Leech Prefix", f"userset {user_id} lprefix", position="header")
        buttons.data_button("Back", f"userset {user_id} leech")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send Leech Filename Prefix. You can add HTML tags. Timeout: 60 sec",
            buttons.build_menu(2, 2),
        )
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "lprefix")
            await update_user_settings(query)
    elif data[2] == "ldest":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get("leech_dest", False)
            or "leech_dest" not in user_dict
            and config_dict["LEECH_DUMP_CHAT"]
        ):
            buttons.data_button("Reset Leech Destination", f"userset {user_id} leech_dest", position="header")
        buttons.data_button("Back", f"userset {user_id} leech")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message,
             "Send leech destination ID/USERNAME/PM. Timeout: 60 sec",
            buttons.build_menu(2, 2),
        )
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "leech_dest")
            await update_user_settings(query)
    elif data[2] == "tlayout":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get("thumb_layout", False)
            or "thumb_layout" not in user_dict
            and config_dict["THUMBNAIL_LAYOUT"]
        ):
            buttons.data_button(
                "Reset Thumbnail Layout", f"userset {user_id} thumb_layout"
            )
        buttons.data_button("Back", f"userset {user_id} leech")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send thumbnail layout (widthxheight, 2x2, 3x3, 2x4, 4x4, ...). Timeout: 60 sec",
            buttons.build_menu(2, 2),
        )
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "thumb_layout")
            await update_user_settings(query)
    elif data[2] == "ex_ex":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get("excluded_extensions", False)
            or "excluded_extensions" not in user_dict
            and global_extension_filter
        ):
            buttons.data_button(
                "Remove Excluded Extensions", f"userset {user_id} excluded_extensions", position="header"
            )
        buttons.data_button("Back", f"userset {user_id} back")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send exluded extenions seperated by space without dot at beginning. Timeout: 60 sec",
            buttons.build_menu(2, 2),
        )
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "excluded_extensions")
            await update_user_settings(query)
    elif data[2] == "name_substitute":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("name_sub", False):
            buttons.data_button("Remove Name Substitute", f"userset {user_id} name_sub")
        buttons.data_button("Back", f"userset {user_id} back")
        buttons.data_button("Close", f"userset {user_id} close")
        emsg = r"""Remove Name
NOTE: You must add \ before any character, those are the characters: \^$.|?*+()[]{}-
Example: script/code/s | mirror/leech | tea/ /s | clone | cpu/ | \[mltb\]/mltb | \\text\\/text/s
1. script will get replaced by code with sensitive case
2. mirror will get replaced by leech
4. tea will get replaced by space with sensitive case
5. clone will get removed
6. cpu will get replaced by space
7. [mltb] will get replaced by mltb
8. \text\ will get replaced by text with sensitive case
"""
        emsg += f"Your Current Value is {user_dict.get('name_sub') or 'not added yet!'}"
        await edit_message(
            message,
            emsg,
            buttons.build_menu(1),
        )
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "name_sub")
            await update_user_settings(query)
    elif data[2] in ["gd", "rc"]:
        await query.answer()
        du = "rc" if data[2] == "gd" else "gd"
        update_user_ldata(user_id, "default_upload", du)
        await update_user_settings(query)
        if config_dict["DATABASE_URL"]:
            await database.update_user_data(user_id)
    elif data[2] == "upload_paths":
        await query.answer()
        buttons = ButtonMaker()
        buttons.data_button("New Path", f"userset {user_id} new_path")
        if user_dict.get(data[2], False):
            buttons.data_button("Show All Paths", f"userset {user_id} show_path")
            buttons.data_button("Remove Path", f"userset {user_id} rm_path")
        buttons.data_button("Back", f"userset {user_id} back")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Add or remove upload path.\n",
            buttons.build_menu(1),
        )
    elif data[2] == "new_path":
        await query.answer()
        buttons = ButtonMaker()
        buttons.data_button("Back", f"userset {user_id} upload_paths")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send path name(no space in name) which you will use it as a shortcut and the path/id seperated by space. You can add multiple names and paths separated by new line. Timeout: 60 sec",
            buttons.build_menu(1),
        )
        event = await conversation_handler(client, query)
        if event:
            await set_option(event, "upload_paths")
            await update_user_settings(query)
    elif data[2] == "rm_path":
        await query.answer()
        buttons = ButtonMaker()
        buttons.data_button("Back", f"userset {user_id} upload_paths")
        buttons.data_button("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send paths names which you want to delete, separated by space. Timeout: 60 sec",
            buttons.build_menu(1),
        )
        event = await conversation_handler(client, query)
        if event:
            await delete_path(event)
            await update_user_settings(query)
    elif data[2] == "show_path":
        await query.answer()
        buttons = ButtonMaker()
        buttons.data_button("Back", f"userset {user_id} upload_paths")
        buttons.data_button("Close", f"userset {user_id} close")
        user_dict = user_data.get(user_id, {})
        msg = "".join(
            f"<b>{key}</b>: <code>{value}</code>\n"
            for key, value in user_dict["upload_paths"].items()
        )
        await edit_message(
            message,
            msg,
            buttons.build_menu(1),
        )
    elif data[2] == "reset":
        await query.answer()
        if ud := user_data.get(user_id, {}):
            if ud and ("is_sudo" in ud or "is_auth" in ud):
                for k in list(ud.keys()):
                    if k not in ["is_sudo", "is_auth"]:
                        del user_data[user_id][k]
            else:
                user_data[user_id].clear()
        await update_user_settings(query)
        if config_dict["DATABASE_URL"]:
            await database.update_user_data(user_id)
        for fpath in [thumb_path, rclone_conf, token_pickle]:
            if await aiopath.exists(fpath):
                await remove(fpath)
    elif data[2] == "back":
        await query.answer()
        await update_user_settings(query)
    else:
        await query.answer()
        await delete_message(message.reply_to_message)
        await delete_message(message)

@new_task
async def send_users_settings(_, message):
    if user_data:
        msg = ""
        for u, d in user_data.items():
            kmsg = f"\n<b>{u}:</b>\n"
            if vmsg := "".join(
                f"{k}: <code>{v}</code>\n" for k, v in d.items() if f"{v}"
            ):
                msg += kmsg + vmsg
        msg_ecd = msg.encode()
        if len(msg_ecd) > 4000:
            with BytesIO(msg_ecd) as ofile:
                ofile.name = "users_settings.txt"
                await send_file(message, ofile)
        else:
            await send_message(message, msg)
    else:
        await send_message(message, "No users data!")


bot.add_handler(
    MessageHandler(
        send_users_settings,
        filters=filters.command(BotCommands.UsersCommand, case_sensitive=True)
        & CustomFilters.sudo,
    )
)
bot.add_handler(
    MessageHandler(
        user_settings,
        filters=filters.command(BotCommands.UserSetCommand, case_sensitive=True)
        & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(edit_user_settings, filters=filters.regex("^userset")))
