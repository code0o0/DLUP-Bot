from aiofiles import open as aiopen
from aiofiles.os import remove, rename, path as aiopath
from aioshutil import rmtree
from asyncio import create_subprocess_exec, create_subprocess_shell, sleep, gather
from dotenv import load_dotenv
from functools import partial
from io import BytesIO
from os import environ, getcwd
from pyrogram.filters import command, regex, create
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from time import time

from bot import (
    config_dict,
    user_data,
    DATABASE_URL,
    MAX_SPLIT_SIZE,
    DRIVES_IDS,
    DRIVES_NAMES,
    INDEX_URLS,
    aria2,
    GLOBAL_EXTENSION_FILTER,
    Intervals,
    aria2_options,
    aria2c_global,
    IS_PREMIUM_USER,
    task_dict,
    qbit_options,
    get_client,
    LOGGER,
    bot,
)
from bot.helper.ext_utils.bot_utils import (
    setInterval,
    sync_to_async,
    new_thread,
)
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.jdownloader_booter import jdownloader
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_utils.rclone_utils.serve import rclone_serve_booter
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    sendFile,
    editMessage,
    update_status_message,
    deleteMessage,
)
from bot.modules.rss import addJob
from bot.modules.torrent_search import initiate_search_tools

START = 0
handler_dict = {}
default_values = {
    "DOWNLOAD_DIR": "/usr/src/app/downloads/",
    "LEECH_SPLIT_SIZE": MAX_SPLIT_SIZE,
    "RSS_DELAY": 600,
    "STATUS_UPDATE_INTERVAL": 15,
    "SEARCH_LIMIT": 0,
    "UPSTREAM_BRANCH": "master",
    "DEFAULT_UPLOAD": "gd",
}


async def get_buttons(key=None, edit_type=None):
    buttons = ButtonMaker()
    if key is None:
        buttons.ibutton("Config Variables", "botset var")
        buttons.ibutton("Qbit Settings", "botset qbit")
        buttons.ibutton("Aria2c Settings", "botset aria")
        buttons.ibutton("Private Files", "botset private")
        buttons.ibutton("JDownloader Sync", "botset syncjd")
        buttons.ibutton("Close", "botset close", position="footer")
        msg = "Bot Settings:"
    elif edit_type is not None:
        if edit_type == "botvar":
            msg = ""
            buttons.ibutton("Default", f"botset resetvar {key}")
            buttons.ibutton("Back", "botset var", position="footer")
            buttons.ibutton("Close", "botset close", position="footer")
            if key in ["CMD_SUFFIX", "OWNER_ID", "USER_SESSION_STRING"]:
                msg += "Restart required for this edit to take effect!\n\n"
            msg += f"Send a valid value for {key}. Current value is '{config_dict[key]}'. Timeout: 60 sec"
        elif edit_type == "ariavar":
            if key != "newkey":
                buttons.ibutton("Default", f"botset resetaria {key}")
                buttons.ibutton("Empty String", f"botset emptyaria {key}")
            buttons.ibutton("Back", "botset aria", position="footer")
            buttons.ibutton("Close", "botset close", position="footer")
            msg = (
                "Send a key with value. Example: https-proxy-user:value"
                if key == "newkey"
                else f"Send a valid value for {key}. Current value is '{aria2_options[key]}'. Timeout: 60 sec"
            )
        elif edit_type == "qbitvar":
            buttons.ibutton("Empty String", f"botset emptyqbit {key}")
            buttons.ibutton("Back", "botset qbit", position="footer")
            buttons.ibutton("Close", "botset close", position="footer")
            msg = f"Send a valid value for {key}. Current value is '{qbit_options[key]}'. Timeout: 60 sec"
    elif key == "var":
        var_list = ["STATUS_UPDATE_INTERVAL", "STATUS_LIMIT", "QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD",
                    "USER_SESSION_STRING", "CMD_SUFFIX", "UPSTREAM_REPO", "UPSTREAM_BRANCH", "BASE_URL_PORT",
                    "BASE_URL", "WEB_PINCODE", "INCOMPLETE_TASK_NOTIFIER", "YT_DLP_OPTIONS", "TORRENT_TIMEOUT",
                    "DEFAULT_UPLOAD", "EXTENSION_FILTER", "USE_SERVICE_ACCOUNTS", "GDRIVE_ID", "STOP_DUPLICATE",
                    "IS_TEAM_DRIVE", "INDEX_URL", "RCLONE_PATH", "RCLONE_FLAGS", "RCLONE_SERVE_URL",
                    "RCLONE_SERVE_PORT", "RCLONE_SERVE_USER", "RCLONE_SERVE_PASS", "LEECH_SPLIT_SIZE", "AS_DOCUMENT", 
                    "EQUAL_SPLITS", "MEDIA_GROUP", "USER_TRANSMISSION", "LEECH_FILENAME_PREFIX", "LEECH_DUMP_CHAT",
                    "JD_EMAIL", "JD_PASS", "FILELION_API", "STREAMWISH_API", "RSS_CHAT", 
                    "RSS_DELAY", "SEARCH_API_LINK", "SEARCH_LIMIT", "SEARCH_PLUGINS"]
        msg = f"Click the button to edit the variable.\n\n"
        for index, k in enumerate(var_list[21*START : 21 + 21*START]):
            value = config_dict[k]
            if not value:
                value = "Not Set"
            elif k == "SEARCH_PLUGINS":
                value = "[......]"
            elif k == "USER_SESSION_STRING":
                value = value[:10] + "..." + value[-10:]
            msg += f'{index+1}. <b>{k}:</b><code>{value}</code>\n'
            buttons.ibutton(index+1, f"botset botvar {k}", position="header")
        pages = (len(var_list) - 1) // 21 + 1
        if START == 0:
            buttons.ibutton("Next Page", "botset start var next")
        elif START == pages - 1:
            buttons.ibutton("Prev Page", "botset start var prev")
        else:
            buttons.ibutton("Prev Page", "botset start var prev")
            buttons.ibutton("Next Page", "botset start var next")
        buttons.ibutton("Back", "botset back", position="footer")
        buttons.ibutton("Close", "botset close", position="footer")
    elif key == "private":
        buttons.ibutton("Back", "botset back", position="footer")
        buttons.ibutton("Close", "botset close", position="footer")
        msg = """Send private file: config.env, token.pickle, rclone.conf, accounts.zip, list_drives.txt, cookies.txt, terabox.txt, .netrc or any other private file!
To delete private file send only the file name as text message.
Note: Changing .netrc will not take effect for aria2c until restart.
Timeout: 60 sec"""
    elif key == "aria":
        msg = f"Click the button to edit the aria2 options.\n\n"
        for index, k in enumerate(aria2_options.keys()):
            msg += f'{index+1}. <b>{k}:</b><code>{aria2_options[k]}</code>\n'
            buttons.ibutton(index+1, f"botset ariavar {k}", position="header")
        buttons.ibutton("Add new key", "botset ariavar newkey")
        buttons.ibutton("Back", "botset back", position="footer")
        buttons.ibutton("Close", "botset close", position="footer")
    elif key == "qbit":
        msg = f"<b>Click the button to edit the qBittorrent options.</b>\n\n"
        for index, k in enumerate(qbit_options.keys()[21*START : 21 + 21*START]):
            msg += f'{index+1}. <b>{k}:</b><code>{qbit_options[k]}</code>\n'
            buttons.ibutton(index+1, f"botset qbitvar {k}", position="header")
        pages = (len(qbit_options) - 1) // 21 + 1
        if START == 0:
            buttons.ibutton("Next Page", "botset start qbit next")
        elif START == 1:
            buttons.ibutton("Prev Page", "botset start qbit prev")

        buttons.ibutton("Back", "botset back", position="footer")
        buttons.ibutton("Close", "botset close", position="footer")

    button = buttons.build_menu(2, 7, 2)
    return msg, button


async def update_buttons(message, key=None, edit_type=None):
    msg, button = await get_buttons(key, edit_type)
    await editMessage(message, msg, button)

async def edit_variable(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
        if key == "INCOMPLETE_TASK_NOTIFIER" and DATABASE_URL:
            await DbManager().trunc_table("tasks")
    elif key in ["LEECH_DUMP_CHAT", "RSS_CHAT"]:
        if value.isdigit() or value.startswith("-"):
            value = int(value)
    elif key == "STATUS_UPDATE_INTERVAL":
        value = int(value)
        if len(task_dict) != 0 and (st := Intervals["status"]):
            for key, intvl in list(st.items()):
                intvl.cancel()
                Intervals["status"][key] = setInterval(
                    value, update_status_message, key
                )
    elif key == "TORRENT_TIMEOUT":
        value = int(value)
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {"bt-stop-timeout": f"{value}"},
                    )
                except Exception as e:
                    LOGGER.error(e)
    elif key == "LEECH_SPLIT_SIZE":
        value = min(int(value), MAX_SPLIT_SIZE)
    elif key == "BASE_URL_PORT":
        value = int(value)
        if config_dict["BASE_URL"]:
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
            await create_subprocess_shell(
                f"gunicorn web.wserver:app --bind 0.0.0.0:{value} --worker-class gevent"
            )
    elif key == "EXTENSION_FILTER":
        fx = value.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.extend(["aria2", "!qB"])
        for x in fx:
            x = x.lstrip(".")
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())
    elif key == "GDRIVE_ID":
        if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
            DRIVES_IDS[0] = value
        else:
            DRIVES_IDS.insert(0, value)
    elif key == "INDEX_URL":
        if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
            INDEX_URLS[0] = value
        else:
            INDEX_URLS.insert(0, value)
    elif value.isdigit():
        value = int(value)
    config_dict[key] = value
    await update_buttons(pre_message, "var")
    await deleteMessage(message)
    if DATABASE_URL:
        await DbManager().update_config({key: value})
    if key in ["SEARCH_PLUGINS", "SEARCH_API_LINK"]:
        await initiate_search_tools()
    elif key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()
    elif key in [
        "RCLONE_SERVE_URL",
        "RCLONE_SERVE_PORT",
        "RCLONE_SERVE_USER",
        "RCLONE_SERVE_PASS",
    ]:
        await rclone_serve_booter()
    elif key in ["JD_EMAIL", "JD_PASS"]:
        jdownloader.initiate()
    elif key == "RSS_DELAY":
        addJob()

async def edit_aria(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "newkey":
        key, value = [x.strip() for x in value.split(":", 1)]
    elif value.lower() == "true":
        value = "true"
    elif value.lower() == "false":
        value = "false"
    if key in aria2c_global:
        await sync_to_async(aria2.set_global_options, {key: value})
    else:
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option, download.gid, {key: value}
                    )
                except Exception as e:
                    LOGGER.error(e)
    aria2_options[key] = value
    await update_buttons(pre_message, "aria")
    await deleteMessage(message)
    if DATABASE_URL:
        await DbManager().update_aria2(key, value)

async def edit_qbit(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif key == "max_ratio":
        value = float(value)
    elif value.isdigit():
        value = int(value)
    await sync_to_async(get_client().app_set_preferences, {key: value})
    qbit_options[key] = value
    await update_buttons(pre_message, "qbit")
    await deleteMessage(message)
    if DATABASE_URL:
        await DbManager().update_qbittorrent(key, value)

async def sync_jdownloader():
    if DATABASE_URL and jdownloader.device is not None:
        await sync_to_async(jdownloader.device.system.exit_jd)
        if await aiopath.exists("cfg.zip"):
            await remove("cfg.zip")
        await sleep(5)
        await (
            await create_subprocess_exec("7z", "a", "cfg.zip", "/JDownloader/cfg")
        ).wait()
        await DbManager().update_private_file("cfg.zip")
        await sync_to_async(jdownloader.connectToDevice)

async def update_private_file(_, message, pre_message):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        fn = file_name.rsplit(".zip", 1)[0]
        if await aiopath.isfile(fn) and file_name != "config.env":
            await remove(fn)
        if fn == "accounts":
            if await aiopath.exists("accounts"):
                await rmtree("accounts")
            if await aiopath.exists("rclone_sa"):
                await rmtree("rclone_sa")
            config_dict["USE_SERVICE_ACCOUNTS"] = False
            if DATABASE_URL:
                await DbManager().update_config({"USE_SERVICE_ACCOUNTS": False})
        elif file_name in [".netrc", "netrc"]:
            await (await create_subprocess_exec("touch", ".netrc")).wait()
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        await deleteMessage(message)
    elif doc := message.document:
        file_name = doc.file_name
        await message.download(file_name=f"{getcwd()}/{file_name}")
        if file_name == "accounts.zip":
            if await aiopath.exists("accounts"):
                await rmtree("accounts")
            if await aiopath.exists("rclone_sa"):
                await rmtree("rclone_sa")
            await (
                await create_subprocess_exec(
                    "7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json"
                )
            ).wait()
            await (
                await create_subprocess_exec("chmod", "-R", "777", "accounts")
            ).wait()
        elif file_name == "list_drives.txt":
            DRIVES_IDS.clear()
            DRIVES_NAMES.clear()
            INDEX_URLS.clear()
            if GDRIVE_ID := config_dict["GDRIVE_ID"]:
                DRIVES_NAMES.append("Main")
                DRIVES_IDS.append(GDRIVE_ID)
                INDEX_URLS.append(config_dict["INDEX_URL"])
            async with aiopen("list_drives.txt", "r+") as f:
                lines = await f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    DRIVES_IDS.append(temp[1])
                    DRIVES_NAMES.append(temp[0].replace("_", " "))
                    if len(temp) > 2:
                        INDEX_URLS.append(temp[2])
                    else:
                        INDEX_URLS.append("")
        elif file_name in [".netrc", "netrc"]:
            if file_name == "netrc":
                await rename("netrc", ".netrc")
                file_name = ".netrc"
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        elif file_name == "config.env":
            load_dotenv("config.env", override=True)
            await load_config()
        if "@github.com" in config_dict["UPSTREAM_REPO"]:
            buttons = ButtonMaker()
            msg = "Push to UPSTREAM_REPO ?"
            buttons.ibutton("Yes!", f"botset push {file_name}")
            buttons.ibutton("No", "botset close")
            await sendMessage(message, msg, buttons.build_menu(2))
        else:
            await deleteMessage(message)
    if file_name == "rclone.conf":
        await rclone_serve_booter()
    await update_buttons(pre_message)
    if DATABASE_URL:
        await DbManager().update_private_file(file_name)
    if await aiopath.exists("accounts.zip"):
        await remove("accounts.zip")


async def event_handler(client, query, pfunc, rfunc, document=False):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = time()
    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(
            user.id == query.from_user.id
            and event.chat.id == chat_id
            and (event.text or event.document and document)
        )
    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )
    while handler_dict[chat_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[chat_id] = False
            await rfunc()
    client.remove_handler(*handler)

@new_thread
async def edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    handler_dict[message.chat.id] = False
    if data[1] == "close":
        await query.answer()
        await deleteMessage(message.reply_to_message)
        await deleteMessage(message)
    elif data[1] == "back":
        await query.answer()
        globals()["START"] = 0
        await update_buttons(message, None)
    elif data[1] == "syncjd":
        if not config_dict["JD_EMAIL"] or not config_dict["JD_PASS"]:
            await query.answer(
                "No Email or Password provided!",
                show_alert=True,
            )
            return
        await query.answer(
            "Syncronization Started. JDownloader will get restarted. It takes up to 5 sec!",
            show_alert=True,
        )
        await sync_jdownloader()
    elif data[1] in ["var", "aria", "qbit"]:
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == "resetvar":
        await query.answer()
        value = ""
        if data[2] in default_values:
            value = default_values[data[2]]
            if (
                data[2] == "STATUS_UPDATE_INTERVAL"
                and len(task_dict) != 0
                and (st := Intervals["status"])
            ):
                for key, intvl in list(st.items()):
                    intvl.cancel()
                    Intervals["status"][key] = setInterval(
                        value, update_status_message, key
                    )
        elif data[2] == "EXTENSION_FILTER":
            GLOBAL_EXTENSION_FILTER.clear()
            GLOBAL_EXTENSION_FILTER.extend(["aria2", "!qB"])
        elif data[2] == "TORRENT_TIMEOUT":
            downloads = await sync_to_async(aria2.get_downloads)
            for download in downloads:
                if not download.is_complete:
                    try:
                        await sync_to_async(
                            aria2.client.change_option,
                            download.gid,
                            {"bt-stop-timeout": "0"},
                        )
                    except Exception as e:
                        LOGGER.error(e)
        elif data[2] == "BASE_URL":
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
        elif data[2] == "BASE_URL_PORT":
            value = 20001
            if config_dict["BASE_URL"]:
                await (
                    await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")
                ).wait()
                await create_subprocess_shell(
                    f"gunicorn web.wserver:app --bind 0.0.0.0:{value} --worker-class gevent"
                )
        elif data[2] == "GDRIVE_ID":
            if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
                DRIVES_NAMES.pop(0)
                DRIVES_IDS.pop(0)
                INDEX_URLS.pop(0)
        elif data[2] == "INDEX_URL":
            if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
                INDEX_URLS[0] = ""
        elif data[2] == "INCOMPLETE_TASK_NOTIFIER" and DATABASE_URL:
            await DbManager().trunc_table("tasks")
        elif data[2] in ["JD_EMAIL", "JD_PASS"]:
            jdownloader.device = None
        config_dict[data[2]] = value
        await update_buttons(message, "var")
        if DATABASE_URL:
            await DbManager().update_config({data[2]: value})
        if data[2] in ["SEARCH_PLUGINS", "SEARCH_API_LINK"]:
            await initiate_search_tools()
        elif data[2] in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
            await start_from_queued()
        elif data[2] in [
            "RCLONE_SERVE_URL",
            "RCLONE_SERVE_PORT",
            "RCLONE_SERVE_USER",
            "RCLONE_SERVE_PASS",
        ]:
            await rclone_serve_booter()
    elif data[1] == "resetaria":
        aria2_defaults = await sync_to_async(aria2.client.get_global_option)
        if aria2_defaults[data[2]] == aria2_options[data[2]]:
            await query.answer("Value already same as you added in aria.sh!")
            return
        await query.answer()
        value = aria2_defaults[data[2]]
        aria2_options[data[2]] = value
        await update_buttons(message, "aria")
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option, download.gid, {data[2]: value}
                    )
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            await DbManager().update_aria2(data[2], value)
    elif data[1] == "emptyaria":
        await query.answer()
        aria2_options[data[2]] = ""
        await update_buttons(message, "aria")
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option, download.gid, {data[2]: ""}
                    )
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            await DbManager().update_aria2(data[2], "")
    elif data[1] == "emptyqbit":
        await query.answer()
        await sync_to_async(get_client().app_set_preferences, {data[2]: value})
        qbit_options[data[2]] = ""
        await update_buttons(message, "qbit")
        if DATABASE_URL:
            await DbManager().update_qbittorrent(data[2], "")
    elif data[1] == "private":
        await query.answer()
        await update_buttons(message, data[1])
        pfunc = partial(update_private_file, pre_message=message)
        rfunc = partial(update_buttons, message)
        await event_handler(client, query, pfunc, rfunc, True)
    elif data[1] == "botvar":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_variable, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "var")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "ariavar":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_aria, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "aria")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "qbitvar":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_qbit, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "var")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "start":
        await query.answer()
        if data[3] == "next":
            globals()["START"] += 1
        elif data[3] == "prev":
            globals()["START"] -= 1
        await update_buttons(message, data[2])
    elif data[1] == "push":
        await query.answer()
        filename = data[2].rsplit(".zip", 1)[0]
        if await aiopath.exists(filename):
            await (
                await create_subprocess_shell(
                    f"git add -f {filename} \
                                                    && git commit -sm botsettings -q \
                                                    && git push origin {config_dict['UPSTREAM_BRANCH']} -qf"
                )
            ).wait()
        else:
            await (
                await create_subprocess_shell(
                    f"git rm -r --cached {filename} \
                                                    && git commit -sm botsettings -q \
                                                    && git push origin {config_dict['UPSTREAM_BRANCH']} -qf"
                )
            ).wait()
        await deleteMessage(message.reply_to_message)
        await deleteMessage(message)

async def bot_settings(_, message):
    handler_dict[message.chat.id] = False
    msg, button = await get_buttons()
    globals()["START"] = 0
    await sendMessage(message, msg, button)

async def load_config():
    STATUS_UPDATE_INTERVAL = environ.get("STATUS_UPDATE_INTERVAL", "")
    if len(STATUS_UPDATE_INTERVAL) == 0:
        STATUS_UPDATE_INTERVAL = 15
    else:
        STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)
    if len(task_dict) != 0 and (st := Intervals["status"]):
        for key, intvl in list(st.items()):
            intvl.cancel()
            Intervals["status"][key] = setInterval(
                STATUS_UPDATE_INTERVAL, update_status_message, key
            )
    STATUS_LIMIT = environ.get("STATUS_LIMIT", "")
    STATUS_LIMIT = 10 if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)
    QUEUE_ALL = environ.get("QUEUE_ALL", "")
    QUEUE_ALL = "" if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)
    QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "")
    QUEUE_DOWNLOAD = "" if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)
    QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
    QUEUE_UPLOAD = "" if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)
    USER_SESSION_STRING = environ.get("USER_SESSION_STRING", "")
    CMD_SUFFIX = environ.get("CMD_SUFFIX", "")
    UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "")
    if len(UPSTREAM_REPO) == 0:
        UPSTREAM_REPO = ""
    UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "")
    if len(UPSTREAM_BRANCH) == 0:
        UPSTREAM_BRANCH = "master"
    #DOWNLOAD
    BASE_URL_PORT = environ.get("BASE_URL_PORT", "")
    BASE_URL_PORT = 20001 if len(BASE_URL_PORT) == 0 else int(BASE_URL_PORT)
    await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
    BASE_URL = environ.get("BASE_URL", "").rstrip("/")
    if len(BASE_URL) == 0:
        BASE_URL = ""
    else:
        await create_subprocess_shell(
            f"gunicorn web.wserver:app --bind 0.0.0.0:{BASE_URL_PORT} --worker-class gevent"
        )
    WEB_PINCODE = environ.get("WEB_PINCODE", "")
    WEB_PINCODE = WEB_PINCODE.lower() == "true"
    INCOMPLETE_TASK_NOTIFIER = environ.get("INCOMPLETE_TASK_NOTIFIER", "")
    INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == "true"
    if not INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        await DbManager().trunc_table("tasks")
    YT_DLP_OPTIONS = environ.get("YT_DLP_OPTIONS", "")
    if len(YT_DLP_OPTIONS) == 0:
        YT_DLP_OPTIONS = ""
    TORRENT_TIMEOUT = environ.get("TORRENT_TIMEOUT", "")
    downloads = aria2.get_downloads()
    if len(TORRENT_TIMEOUT) == 0:
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {"bt-stop-timeout": "0"},
                    )
                except Exception as e:
                    LOGGER.error(e)
        TORRENT_TIMEOUT = ""
    else:
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {"bt-stop-timeout": TORRENT_TIMEOUT},
                    )
                except Exception as e:
                    LOGGER.error(e)
        TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)
    #UPLOAD
    DEFAULT_UPLOAD = environ.get("DEFAULT_UPLOAD", "")
    if DEFAULT_UPLOAD != "rc":
        DEFAULT_UPLOAD = "gd"
    EXTENSION_FILTER = environ.get("EXTENSION_FILTER", "")
    if len(EXTENSION_FILTER) > 0:
        fx = EXTENSION_FILTER.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.extend(["aria2", "!qB"])
        for x in fx:
            if x.strip().startswith("."):
                x = x.lstrip(".")
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())
    USE_SERVICE_ACCOUNTS = environ.get("USE_SERVICE_ACCOUNTS", "")
    USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == "true"
    # GDrive Tools
    GDRIVE_ID = environ.get("GDRIVE_ID", "")
    if len(GDRIVE_ID) == 0:
        GDRIVE_ID = ""
    STOP_DUPLICATE = environ.get("STOP_DUPLICATE", "")
    STOP_DUPLICATE = STOP_DUPLICATE.lower() == "true"
    IS_TEAM_DRIVE = environ.get("IS_TEAM_DRIVE", "")
    IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == "true"
    INDEX_URL = environ.get("INDEX_URL", "").rstrip("/")
    if len(INDEX_URL) == 0:
        INDEX_URL = ""
    # Rclone
    RCLONE_PATH = environ.get("RCLONE_PATH", "")
    if len(RCLONE_PATH) == 0:
        RCLONE_PATH = ""
    RCLONE_FLAGS = environ.get("RCLONE_FLAGS", "")
    if len(RCLONE_FLAGS) == 0:
        RCLONE_FLAGS = ""
    RCLONE_SERVE_URL = environ.get("RCLONE_SERVE_URL", "").rstrip("/")
    if len(RCLONE_SERVE_URL) == 0:
        RCLONE_SERVE_URL = ""
    RCLONE_SERVE_PORT = environ.get("RCLONE_SERVE_PORT", "")
    RCLONE_SERVE_PORT = 20002 if len(RCLONE_SERVE_PORT) == 0 else int(RCLONE_SERVE_PORT)
    RCLONE_SERVE_USER = environ.get("RCLONE_SERVE_USER", "")
    if len(RCLONE_SERVE_USER) == 0:
        RCLONE_SERVE_USER = ""
    RCLONE_SERVE_PASS = environ.get("RCLONE_SERVE_PASS", "")
    if len(RCLONE_SERVE_PASS) == 0:
        RCLONE_SERVE_PASS = ""
    # Leech
    MAX_SPLIT_SIZE = 4194304000 if IS_PREMIUM_USER else 2097152000
    LEECH_SPLIT_SIZE = environ.get("LEECH_SPLIT_SIZE", "")
    if len(LEECH_SPLIT_SIZE) == 0 or int(LEECH_SPLIT_SIZE) > MAX_SPLIT_SIZE:
        LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
    else:
        LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE)
    AS_DOCUMENT = environ.get("AS_DOCUMENT", "")
    AS_DOCUMENT = AS_DOCUMENT.lower() == "true"
    EQUAL_SPLITS = environ.get("EQUAL_SPLITS", "")
    EQUAL_SPLITS = EQUAL_SPLITS.lower() == "true"
    MEDIA_GROUP = environ.get("MEDIA_GROUP", "")
    MEDIA_GROUP = MEDIA_GROUP.lower() == "true"
    USER_TRANSMISSION = environ.get("USER_TRANSMISSION", "")
    USER_TRANSMISSION = USER_TRANSMISSION.lower() == "true" and IS_PREMIUM_USER
    LEECH_FILENAME_PREFIX = environ.get("LEECH_FILENAME_PREFIX", "")
    if len(LEECH_FILENAME_PREFIX) == 0:
        LEECH_FILENAME_PREFIX = ""
    LEECH_DUMP_CHAT = environ.get("LEECH_DUMP_CHAT", "")
    LEECH_DUMP_CHAT = "" if len(LEECH_DUMP_CHAT) == 0 else LEECH_DUMP_CHAT
    if LEECH_DUMP_CHAT.isdigit() or LEECH_DUMP_CHAT.startswith("-"):
        LEECH_DUMP_CHAT = int(LEECH_DUMP_CHAT)
    # Additional
    JD_EMAIL = environ.get("JD_EMAIL", "")
    JD_PASS = environ.get("JD_PASS", "")
    if len(JD_EMAIL) == 0 or len(JD_PASS) == 0:
        JD_EMAIL = ""
        JD_PASS = ""
    FILELION_API = environ.get("FILELION_API", "")
    if len(FILELION_API) == 0:
        FILELION_API = ""
    STREAMWISH_API = environ.get("STREAMWISH_API", "")
    if len(STREAMWISH_API) == 0:
        STREAMWISH_API = ""
    RSS_CHAT = environ.get("RSS_CHAT", "")
    RSS_CHAT = "" if len(RSS_CHAT) == 0 else RSS_CHAT
    if RSS_CHAT.isdigit() or RSS_CHAT.startswith("-"):
        RSS_CHAT = int(RSS_CHAT)
    RSS_DELAY = environ.get("RSS_DELAY", "")
    RSS_DELAY = 600 if len(RSS_DELAY) == 0 else int(RSS_DELAY)
    SEARCH_API_LINK = environ.get("SEARCH_API_LINK", "").rstrip("/")
    if len(SEARCH_API_LINK) == 0:
        SEARCH_API_LINK = ""
    SEARCH_LIMIT = environ.get("SEARCH_LIMIT", "")
    SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)
    SEARCH_PLUGINS = environ.get("SEARCH_PLUGINS", "")
    if len(SEARCH_PLUGINS) == 0:
        SEARCH_PLUGINS = ""

    DRIVES_IDS.clear()
    DRIVES_NAMES.clear()
    INDEX_URLS.clear()
    if GDRIVE_ID:
        DRIVES_NAMES.append("Main")
        DRIVES_IDS.append(GDRIVE_ID)
        INDEX_URLS.append(INDEX_URL)
    if await aiopath.exists("list_drives.txt"):
        async with aiopen("list_drives.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                DRIVES_IDS.append(temp[1])
                DRIVES_NAMES.append(temp[0].replace("_", " "))
                if len(temp) > 2:
                    INDEX_URLS.append(temp[2])
                else:
                    INDEX_URLS.append("")
    config_dict.update(
        {
            'STATUS_UPDATE_INTERVAL': STATUS_UPDATE_INTERVAL,
            'STATUS_LIMIT': STATUS_LIMIT,
            'QUEUE_ALL': QUEUE_ALL,
            'QUEUE_DOWNLOAD': QUEUE_DOWNLOAD,
            'QUEUE_UPLOAD': QUEUE_UPLOAD,
            'USER_SESSION_STRING': USER_SESSION_STRING,
            'CMD_SUFFIX': CMD_SUFFIX,
            'UPSTREAM_REPO': UPSTREAM_REPO,
            'UPSTREAM_BRANCH': UPSTREAM_BRANCH,
            'BASE_URL_PORT': BASE_URL_PORT,
            'BASE_URL': BASE_URL,
            'WEB_PINCODE': WEB_PINCODE,
            'INCOMPLETE_TASK_NOTIFIER': INCOMPLETE_TASK_NOTIFIER,
            'YT_DLP_OPTIONS': YT_DLP_OPTIONS,
            'TORRENT_TIMEOUT': TORRENT_TIMEOUT,
            'DEFAULT_UPLOAD': DEFAULT_UPLOAD,
            'EXTENSION_FILTER': EXTENSION_FILTER,
            'USE_SERVICE_ACCOUNTS': USE_SERVICE_ACCOUNTS,
            'GDRIVE_ID': GDRIVE_ID,
            'STOP_DUPLICATE': STOP_DUPLICATE,
            'IS_TEAM_DRIVE': IS_TEAM_DRIVE,
            'INDEX_URL': INDEX_URL,
            'RCLONE_PATH': RCLONE_PATH,
            'RCLONE_FLAGS': RCLONE_FLAGS,
            'RCLONE_SERVE_URL': RCLONE_SERVE_URL,
            'RCLONE_SERVE_PORT': RCLONE_SERVE_PORT,
            'RCLONE_SERVE_USER': RCLONE_SERVE_USER,
            'RCLONE_SERVE_PASS': RCLONE_SERVE_PASS,
            'LEECH_SPLIT_SIZE': LEECH_SPLIT_SIZE,
            'AS_DOCUMENT': AS_DOCUMENT,
            'EQUAL_SPLITS': EQUAL_SPLITS,
            'MEDIA_GROUP': MEDIA_GROUP,
            'USER_TRANSMISSION': USER_TRANSMISSION,
            'LEECH_FILENAME_PREFIX': LEECH_FILENAME_PREFIX,
            'LEECH_DUMP_CHAT': LEECH_DUMP_CHAT,
            'JD_EMAIL': JD_EMAIL,
            'JD_PASS': JD_PASS,
            'FILELION_API': FILELION_API,
            'STREAMWISH_API': STREAMWISH_API,
            'RSS_CHAT': RSS_CHAT,
            'RSS_DELAY': RSS_DELAY,
            'SEARCH_API_LINK': SEARCH_API_LINK,
            'SEARCH_LIMIT': SEARCH_LIMIT,
            'SEARCH_PLUGINS': SEARCH_PLUGINS
        }
    )
    if DATABASE_URL:
        await DbManager().update_config(config_dict)
    await gather(initiate_search_tools(), start_from_queued(), rclone_serve_booter())
    addJob()


bot.add_handler(
    MessageHandler(
        bot_settings, filters=command(BotCommands.BotSetCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    CallbackQueryHandler(
        edit_bot_settings, filters=regex("^botset") & CustomFilters.sudo
    )
)