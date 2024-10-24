from asyncio import create_subprocess_exec, create_subprocess_shell, gather, wait_for
from os import environ, getcwd
from os import path as ospath
import secrets

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove, rename
from dotenv import load_dotenv
from pyrogram import filters
from pyrogram.errors import ListenerStopped, ListenerTimeout
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import (
    CONFIG_DIR,
    LOGGER,
    aria2,
    aria2_options,
    bot,
    config_dict,
    intervals,
    jd_lock,
    jd_options,
    nzb_options,
    qbit_options,
    qbittorrent_client,
    fb_options,
    sabnzbd_client,
    task_dict,
    BASE_URL_PORT
)

from ..helper.ext_utils.bot_utils import (
    SetInterval,
    new_task,
    retry_function,
    sync_to_async,
)
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.jdownloader_booter import jdownloader
from ..helper.ext_utils.task_manager import start_from_queued
from ..helper.mirror_leech_utils.rclone_utils.serve import (
    rclone_serve_booter,
    rclone_serve_shutdown,
)
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
    update_status_message,
)
from .rss import add_job
from .torrent_search import initiate_search_tools

bs_start = 0

def get_content_buttons(content_dict, edit_type="", page_type=""):
    msg = ""
    buttons = ButtonMaker()
    for index, key in enumerate(list(content_dict.keys())[18*bs_start : 18 + 18*bs_start]):
        value = str(content_dict[key])
        if not value:
            value = "None"
        elif len(value) > 15:
            value = value[:3] + "…" + value[-3:]
        index = 18*bs_start + index +1
        msg += f'{index}. <b>{key}</b> is <u>{value}</u>\n'
        buttons.data_button(index, f"botset {edit_type} {key}", position="header")
    pages = (len(content_dict) - 1) // 18 + 1
    if pages == 1:
        pass
    elif bs_start == 0:
        buttons.data_button("Next Page", f"botset start {page_type} next")
    elif bs_start == pages - 1:
        buttons.data_button("Prev Page", f"botset start {page_type} prev")
    else:
        buttons.data_button("Prev Page", f"botset start {page_type} prev")
        buttons.data_button("Next Page", f"botset start {page_type} next")
    msg += "<pre>🔔<b>NOTE:</b> Click on the button below to select an option.</pre>"
    return buttons, msg

async def get_buttons(edit_type=None, key=None):
    buttons = ButtonMaker()
    if edit_type is None:
        buttons.data_button("Config Variables", "botset var")
        buttons.data_button("Private Files", "botset private")
        buttons.data_button("Aria2c Settings", "botset aria")
        buttons.data_button("Qbit Settings", "botset qbit")
        buttons.data_button("Sabnzbd Settings", "botset nzb")
        buttons.data_button("JDownloader Settings", "botset jdownloader")
        buttons.data_button("FileBrowser Settings", "botset fb")
        buttons.data_button("Close", "botset close", position="footer")
        msg = "Bot Settings:"
    elif edit_type in ["var", "private", "aria", "qbit", "fb", "nzb", "jdownloader"]:
        if edit_type == "var":
            var_list = [
                "STATUS_UPDATE_INTERVAL", "STATUS_LIMIT", "QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD",
                "USER_SESSION_STRING", "CMD_SUFFIX", "BASE_URL", "WEB_PINCODE", "INCOMPLETE_TASK_NOTIFIER",
                "TORRENT_TIMEOUT", "USENET_SERVERS", "FILELION_API", "STREAMWISH_API", "RSS_CHAT", "RSS_DELAY",
                "SEARCH_API_LINK", "SEARCH_LIMIT", "SEARCH_PLUGINS"
                ]
            content_dict = {k: config_dict[k] for k in var_list}
            buttons, msg = get_content_buttons(content_dict, "botvar", "var")
            buttons.data_button("Default", "botset resetvar", position="body")
            buttons.data_button("Back", "botset back", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
        elif edit_type == "private":
            buttons.data_button("Back", "botset back", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
            msg = "Send private file: cookies.txt, .netrc or any other private file!\n"
            msg += "<b>Note:</b> To delete private file send only the file name as text message.Changing .netrc will not take effect for aria2c until restart.\n"
            msg += "<b>Timeout:</b> 30 sec"
        elif edit_type == "aria":
            buttons, msg = get_content_buttons(aria2_options, "ariavar", "aria")
            buttons.data_button("Back", "botset back", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
        elif edit_type == "qbit":
            buttons, msg = get_content_buttons(qbit_options, "qbitvar", "qbit")
            if qbit_options["web_ui_address"] != "*":
                buttons.data_button("Start WebUI", "botset qbwebui", position="body")
            else:
                buttons.data_button("Stop WebUI", "botset qbwebui", position="body")
            buttons.data_button("Sync Qbittorrent", "botset syncqbit", position="body")
            buttons.data_button("Back", "botset back", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
        elif edit_type == "fb":
            for index, key in enumerate(list(fb_options.keys()), 1):
                value = str(fb_options[key])
                msg += f'{index}. <b>{key}</b> is <u>{value}</u>\n'
            buttons.data_button("Reset Password", "botset fbpwd")
            buttons.data_button("Reset Config", "botset fbconfig")
            if fb_options["enable"]:
                buttons.data_button("Stop FileBrowser", "botset fbserve", position="body")
            else:
                buttons.data_button("Start FileBrowser", "botset fbserve", position="body")
            buttons.data_button("Back", "botset back", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
        elif edit_type == "nzb":
            buttons, msg = get_content_buttons(nzb_options, "nzbvar", "nzb")
            buttons.data_button("Servers", "botset nzbvar nzbserver", position="body")
            buttons.data_button("Sync Sabnzbd", "botset syncnzb", position="body")
            if nzb_options["inet_exposure"] == 0:
                buttons.data_button("Start WebUI", "botset nzbwebui", position="body")
            else:
                buttons.data_button("Stop WebUI", "botset nzbwebui", position="body")
            buttons.data_button("Default", "botset resetnzb", position="body")
            buttons.data_button("Back", "botset back", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
        elif edit_type == "jdownloader":
            buttons, msg = get_content_buttons(jd_options, "jdvar", "jdownloader")
            buttons.data_button("Sync Config", "botset jdsync", position="body")
            buttons.data_button("Back", "botset back", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
    elif edit_type in ["botvar", "ariavar", "qbitvar", "nzbvar", "jdvar"]:
        if edit_type == "botvar":
            msg = ""
            buttons.data_button("Back", "botset back var", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
            if key in ["CMD_SUFFIX", "OWNER_ID", "USER_SESSION_STRING"]:
                msg += "Restart required for this edit to take effect!\n\n"
            msg += f"Send a valid value for <b>{key}</b>.\nCurrent value is <b>'{config_dict[key]}'</b>.\n"
            msg += "<b>Timeout:</b> 30 sec"
        elif edit_type == "ariavar":
            buttons.data_button("Back", "botset back aria", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
            msg = f"Send a valid value for <b>{key}</b>.\nCurrent value is <b>'{aria2_options[key]}'</b>.\n" 
            msg += "<b>Timeout:</b> 30 sec"
        elif edit_type == "qbitvar":
            buttons.data_button("Back", "botset back qbit", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
            msg = f"Send a valid value for <b>{key}</b>.\nCurrent value is <b>'{qbit_options[key]}'</b>.\n"
            msg += "<b>Timeout:</b> 30 sec"
        elif edit_type == "nzbvar" and key != "nzbserver":
            buttons.data_button("Back", "botset back nzb", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
            msg = f"Send a valid value for <b>{key}</b>.\nCurrent value is <b>'{nzb_options[key]}'</b>.\n"
            msg += "<b>Note:</b> If the value is list then seperate them by space or ,\nExample: .exe,info or .exe .info\n"
            msg += "<b>Timeout:</b> 30 sec"
        elif edit_type == "nzbvar":
            if len(config_dict["USENET_SERVERS"]) > 0:
                content_dict = {f"nzbser{index}": k["name"] for index, k in enumerate(config_dict["USENET_SERVERS"])}
                buttons, msg = get_content_buttons(content_dict, "nzbserver", "nzbvar")
            else:
                msg = "No servers found!"
            msg += "<pre>🔔<b>NOTE:</b> Click on the button below to select an option.</pre>"
            buttons.data_button("Add New", "botset nzbserver newser", position="body")
            buttons.data_button("Back", "botset back nzb", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
        elif edit_type == "jdvar":
            buttons.data_button("Back", "botset back jdownloader", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
            msg = f"Send a valid value for <b>{key}</b>.\nCurrent value is <b>'{jd_options[key]}'</b>.\n"
            msg += "<b>Timeout:</b> 30 sec"
    elif edit_type == "nzbserver":
        if key.startswith("nzbser"):
            msg = ""
            index = int(key.replace("nzbser", ""))
            content_dict = config_dict["USENET_SERVERS"][index]
            buttons, msg = get_content_buttons(content_dict, f"nzbsevar{index}", "nzbser")
            buttons.data_button("Remove Server", f"botset remser {index}", position="body")
            buttons.data_button("Back", "botset back nzbvar nzbserver", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
        else:
            msg = "Send one server as dictionary {}, like in config.env without [].\n"
            msg += "<b>Timeout:</b> 30 sec"
            buttons.data_button("Back", "botset back nzbvar nzbserver", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
    elif edit_type.startswith("nzbsevar"):
        index = int(edit_type.replace("nzbsevar", ""))
        buttons.data_button("Back", f"botset back nzbserver nzbser{index}", position="footer")
        buttons.data_button("Close", "botset close", position="footer")
        msg = f"Send a valid value for <b>{key}</b> in server {config_dict['USENET_SERVERS'][index]['name']}.\n"
        msg += f"Current value is <b>'{config_dict['USENET_SERVERS'][index][key]}'</b>.\n"
        msg += "<b>Timeout:</b> 30 sec"
    button = buttons.build_menu(2, 6, 4, 2)
    return msg, button


async def update_buttons(message, edit_type=None, key=None):
    msg, button = await get_buttons(edit_type, key)
    await edit_message(message, msg, button)

async def edit_variable(message, pre_message, key):
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
        if key == "INCOMPLETE_TASK_NOTIFIER" and config_dict["DATABASE_URL"]:
            await database.trunc_table("tasks")
    elif key == "STATUS_UPDATE_INTERVAL":
        value = int(value)
        if len(task_dict) != 0 and (st := intervals["status"]):
            for cid, intvl in list(st.items()):
                intvl.cancel()
                intervals["status"][cid] = SetInterval(
                    value, update_status_message, cid
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
    elif value.isdigit():
        value = int(value)
    elif value.startswith("[") and value.endswith("]"):
        value = eval(value)
    config_dict[key] = value
    await update_buttons(pre_message, "var")
    await delete_message(message)
    await database.update_config()
    if key in ["SEARCH_PLUGINS", "SEARCH_API_LINK"]:
        await initiate_search_tools()
    elif key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()
    elif key == "RSS_DELAY":
        add_job()
    elif key == "USET_SERVERS":
        for s in value:
            await sabnzbd_client.set_special_config("servers", s)

async def edit_aria(message, pre_message, key):
    value = message.text
    if value.lower() == "true":
        value = "true"
    elif value.lower() == "false":
        value = "false"
    elif value.lower() == "none":
        value = ""
    await sync_to_async(aria2.set_global_options, {key: value})
    aria2_options[key] = value
    await update_buttons(pre_message, "aria")
    await delete_message(message)
    await database.update_aria2()

async def edit_qbit(message, pre_message, key):
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif value.lower() == "none":
        value = ""
    elif key == "max_ratio":
        value = float(value)
    elif value.isdigit():
        value = int(value)
    await sync_to_async(qbittorrent_client.app_set_preferences, {key: value})
    qbit_options[key] = value
    await update_buttons(pre_message, "qbit")
    await delete_message(message)
    await database.update_qbittorrent()

async def edit_nzb(message, pre_message, key):
    value = message.text
    if value.isdigit():
        value = int(value)
    elif value.lower() == "none":
        value = ""
    elif value.startswith("[") and value.endswith("]"):
        value = ",".join(eval(value))
    if key == "inet_exposure":
        async with aiopen('sabnzbd/SABnzbd.ini', 'r', encoding='utf-8') as file:
            lines = file.readlines()
        async with aiopen('sabnzbd/SABnzbd.ini', 'w', encoding='utf-8') as file:
            for line in lines:
                if line.startswith("inet_exposure"):
                    file.write(f"{key} = {value}\n")
                else:
                    file.write(line)
        nzb_options[key] = value
        await sabnzbd_client.restart()
    else:
        res = await sabnzbd_client.set_config("misc", key, value)
        nzb_options[key] = res["config"]["misc"][key]
    await update_buttons(pre_message, "nzb")
    await delete_message(message)
    await database.update_nzb_config()

async def edit_jdownloader(message, pre_message, key):
    value = message.text
    if value.lower() == "none":
        value = ""
    jd_options[key] = value
    jdownloader.initiate()
    await update_buttons(pre_message, "jdownloader")
    await delete_message(message)
    await database.update_jdownloader()

async def edit_nzb_server(message, pre_message, key, index=0):
    value = message.text
    if value.lower() == "none":
        value = ""
    elif value.startswith("{") and value.endswith("}"):
        if key == "newser":
            try:
                value = eval(value)
            except Exception as e:
                await send_message(message, "Invalid dict format!")
                await update_buttons(pre_message, edit_type="nzbvar", key="nzbserver")
                LOGGER.error(f"Error in nzb server dict format: {e}")
                return
            res = await sabnzbd_client.add_server(value)
            if not res["config"]["servers"][0]["host"]:
                await send_message(message, "Invalid server!")
                await update_buttons(pre_message, edit_type="nzbvar", key="nzbserver")
                return
            config_dict["USENET_SERVERS"].append(value)
            await update_buttons(pre_message, edit_type="nzbvar", key="nzbserver")
    elif key != "newser":
        if value.isdigit():
            value = int(value)
        res = await sabnzbd_client.add_server(
            {"name": config_dict["USENET_SERVERS"][index]["name"], key: value}
        )
        if res["config"]["servers"][0][key] == "":
            await send_message(message, "Invalid value")
            return
        config_dict["USENET_SERVERS"][index][key] = value
        await update_buttons(pre_message, f"nzbser{index}")
    await delete_message(message)
    await database.update_config()

async def sync_jdownloader():
    async with jd_lock:
        if jdownloader.device is None:
            return
        try:
            await wait_for(retry_function(jdownloader.update_devices), timeout=10)
        except Exception as e:
            LOGGER.error(f"Error updating devices: {e}")
            is_connected = await jdownloader.jdconnect()
            if not is_connected:
                LOGGER.error(jdownloader.error)
                return
            isDeviceConnected = await jdownloader.connectToDevice()
            if not isDeviceConnected:
                LOGGER.error(jdownloader.error)
                return
        await jdownloader.device.system.exit_jd()
        is_connected = await jdownloader.jdconnect()
        if not is_connected:
            LOGGER.error(jdownloader.error)
            return
        isDeviceConnected = await jdownloader.connectToDevice()
        if not isDeviceConnected:
            LOGGER.error(jdownloader.error)
    if await aiopath.exists("/JDownloader/cfg.zip"):
        await remove("/JDownloader/cfg.zip")
    await (
        await create_subprocess_exec("7z", "a", "/JDownloader/cfg.zip", "/JDownloader/cfg")
    ).wait()
    await database.update_user_doc(0, "/JDownloader/cfg.zip")

async def update_private_file(message, pre_message):
    if not message.media and (file_name := message.text):
        if file_name == "config.env":
            LOGGER.error("Cannot change config.env file!")
        elif await aiopath.isfile(file_name):
            await remove(file_name)  
        if file_name in [".netrc", "netrc"]:
            await (await create_subprocess_exec("touch", ".netrc")).wait()
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
    elif doc := message.document:
        file_name = doc.file_name
        await message.download(file_name=f"{getcwd()}/{file_name}")
        if file_name in [".netrc", "netrc"]:
            if file_name == "netrc":
                await rename("netrc", ".netrc")
                file_name = ".netrc"
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        elif file_name == "config.env":
            file_name = ospath.join(CONFIG_DIR, "config.env")
            load_dotenv(file_name, override=True)
            await load_config()
    await delete_message(message)
    await update_buttons(pre_message)
    await database.update_user_doc(0, file_name)

async def conversation_handler(client, query, document=False, edit_type=None, key=None):
    message = query.message
    from_user = query.from_user
    try:
        response_message = await client.listen(
            chat_id=message.chat.id,
            user_id=from_user.id,
            message_id=message.id,
            filters=filters.text | filters.document if document else filters.text,
            timeout=30,
        )
    except ListenerTimeout:
        await update_buttons(message, edit_type, key)
        return
    except ListenerStopped:
        return
    return response_message

@new_task
async def edit_bot_settings(client, query):
    message = query.message
    await client.stop_listening(
        chat_id=message.chat.id,
        user_id=query.from_user.id,
        )
    data = query.data.split()
    if data[1] == "close":
        await query.answer()
        await delete_message(message.reply_to_message)
        await delete_message(message)
    elif data[1] == "back":
        await query.answer()
        globals()["bs_start"] = 0
        edit_type = data[2] if len(data) > 2 else None
        key = data[3] if len(data) > 3 else None
        await update_buttons(message, edit_type, key)
    elif data[1] == "bs_start":
        await query.answer()
        if data[3] == "next":
            globals()["bs_start"] += 1
        elif data[3] == "prev":
            globals()["bs_start"] -= 1
        await update_buttons(message, data[2])

    elif data[1] in ["var", "private", "aria", "qbit", "fb", "nzb", "jdownloader"]:
        await query.answer()
        await update_buttons(message, data[1])
        event = (
            await conversation_handler(client, query, True) 
            if data[1] == "private" else None
            )
        if event:
            await update_private_file(event, message)

    elif data[1] == "botvar":
        await query.answer()
        await update_buttons(message, data[1], data[2])
        event = await conversation_handler(client, query, edit_type="var")
        if event:
            await edit_variable(event, message, data[2])
    elif data[1] == "ariavar":
        await query.answer()
        await update_buttons(message, data[1], data[2])
        event = await conversation_handler(client, query, edit_type="aria")
        if event:
            await edit_aria(event, message, data[2])
    elif data[1] == "qbitvar":
        await query.answer()
        await update_buttons(message, data[1], data[2])
        event = await conversation_handler(client, query, edit_type="qbit")
        if event:
            await edit_qbit(event, message, data[2])
    elif data[1] == "nzbvar":
        await query.answer()
        if data[2] == "nzbserver":
            globals()["bs_start"] = 0
        await update_buttons(message, data[1], data[2])
        event = (
            await conversation_handler(client, query, edit_type="nzb")
            if data[2] != "nzbserver" else None
        )
        if event:
            await edit_nzb(event, message, data[2])
    elif data[1] == "jdvar":
        await query.answer()
        await update_buttons(message, data[1], data[2])
        event = await conversation_handler(client, query, edit_type="jdownloader")
        if event:
            await edit_jdownloader(event, message, data[2])
    
    elif data[1] == "resetvar":
        await query.answer()
        load_dotenv(ospath.join(CONFIG_DIR, "config.env"), override=True)
        await load_config()
        await update_buttons(message, "var")
    elif data[1] == "syncqbit":
        await query.answer(
            "Syncronization Started. It takes up to 2 sec!", show_alert=True
        )
        _dict = await sync_to_async(qbittorrent_client.get_app_preferences())
        qbit_options.update(
            {k: v for k, v in _dict.items() if not k.startswith(("rss", "listen_port"))}
        )
        await database.update_qbittorrent()
    elif data[1] == "qbwebui":
        if qbit_options["web_ui_address"] == "*":
            qbit_options["web_ui_address"] = "127.0.0.1"
            await query.answer("WebUI Stopped", show_alert=True)
            await sync_to_async(qbittorrent_client.app_set_preferences, {"web_ui_address": "127.0.0.1"})
            await database.update_qbittorrent()
        else:
            qbit_options["web_ui_address"] = "*"
            await query.answer("WebUI Started!", show_alert=True)
            await sync_to_async(qbittorrent_client.app_set_preferences, {"web_ui_address": "*"})
            await database.update_qbittorrent()
        await update_buttons(message, "qbit")
    elif data[1] == "fbserve":
        if fb_options["enable"]:
            fb_options["enable"] = False
            await query.answer("FileBrowser Stopped!", show_alert=True)
            await create_subprocess_exec("pkill", "-9", "-f", "filebrowser")
        else:
            fb_options["enable"] = True
            await query.answer("FileBrowser Started!", show_alert=True)
            await create_subprocess_shell(
                "nohup", "filebrowser", "--database", f"{CONFIG_DIR}/filebrowser.db", "> /dev/null", "2>&1", "&",
            )
        await update_buttons(message, "fb")
        await database.update_filebrowser()
    elif data[1] in ["fbpwd", "fbconfig"]:
        if fb_options["enable"]:
            await (await create_subprocess_exec("pkill", "-9", "-f", "filebrowser")).wait()
        if data[1] == "fbpwd":
            fb_options["password"] = secrets.token_urlsafe(8)
            await (await create_subprocess_exec(
                "filebrowser", "users", "update", fb_options["user"], "--password", fb_options["password"],
                "--database", f"{CONFIG_DIR}/filebrowser.db"
            )).wait()
            await database.update_filebrowser()
            await query.answer("Password Reset!", show_alert=True)
        elif data[1] == "fbconfig":
            await (await create_subprocess_exec(
                "filebrowser", "config", "import", f"{getcwd()}/filebrowser/filebrowser.yaml",
                "--database", f"{CONFIG_DIR}/filebrowser.db"
            )).wait()
            await query.answer("Config Reset!", show_alert=True)
        if fb_options["enable"]:
            await create_subprocess_shell(
                "nohup", "filebrowser", "--database", f"{CONFIG_DIR}/filebrowser.db", "> /dev/null", "2>&1", "&",
            )
    elif data[1] == "syncnzb":
        await query.answer(
            "Syncronization Started. It takes up to 2 sec!", show_alert=True
        )
        _dict = await sabnzbd_client.get_config()
        nzb_options.update(_dict["config"]["misc"])
        await update_buttons(message, "nzb")
        await database.update_nzb_config()
    elif data[1] == "nzbwebui":
        if nzb_options["inet_exposure"] == 0:
            nzb_options["inet_exposure"] = 4
            await query.answer("WebUI Started", show_alert=True)
        else:
            nzb_options["inet_exposure"] = 0
            await query.answer("WebUI Stopped!", show_alert=True)
        async with aiopen('sabnzbd/SABnzbd.ini', 'r', encoding='utf-8') as file:
                lines = file.readlines()
        async with aiopen('sabnzbd/SABnzbd.ini', 'w', encoding='utf-8') as file:
            for line in lines:
                if line.startswith("inet_exposure"):
                    file.write(f"inet_exposure = {nzb_options['inet_exposure']}\n")
                else:
                    file.write(line)
        await update_buttons(message, "nzb")
        await sabnzbd_client.restart()
        await database.update_nzb_config()
    elif data[1] == "resetnzb":
        res = await sabnzbd_client.set_config_default([key for key in nzb_options.keys()])
        if not res['status']:
            await query.answer(f"Failed to reset {data[2]}!", show_alert=True)
            return
        await query.answer(f"{data[2]} has been reset to default!", show_alert=True)
        nzb_options.update(await sabnzbd_client.get_config()['config']['misc'])
        await update_buttons(message, "nzb")
        await database.update_nzb_config()
    elif data[1] == "jdsync":
        if not jd_options["jd_email"] or not jd_options["jd_passwd"]:
            await query.answer("No Email or Password provided!", show_alert=True)
            return
        await query.answer(
            "Syncronization Started. JDownloader will get restarted. It takes up to 10 sec!",
            show_alert=True,
        )
        await sync_jdownloader()
    
    elif data[1] == "nzbserver":
        await query.answer()
        await update_buttons(message, data[1], data[2])
        event = (
            await conversation_handler(client, query, edit_type="nzbvar", key="nzbserver")
            if data[2] == "newser" else None
        )
        if event:
            await edit_nzb_server(event, message, data[2])
    elif data[1] == "remser":
        index = int(data[2])
        await sabnzbd_client.delete_config(
            "servers", config_dict["USENET_SERVERS"][index]["name"]
        )
        del config_dict["USENET_SERVERS"][index]
        await update_buttons(message, "nzbvar", "nzbserver")
        await database.update_config()
    elif data[1].startswith("nzbsevar"):
        index = int(data[1].replace("nzbsevar", ""))
        await query.answer()
        await update_buttons(message, data[1], data[2])
        event = await conversation_handler(client, query, edit_type="nzbserver", key=f"nzbser{index}")
        if event:
            await edit_nzb_server(event, message, data[2], index)

@new_task
async def bot_settings(client, message):
    msg, button = await get_buttons()
    globals()["bs_start"] = 0
    await send_message(message, msg, button)

async def load_config():
    STATUS_UPDATE_INTERVAL = environ.get("STATUS_UPDATE_INTERVAL", "")
    if len(STATUS_UPDATE_INTERVAL) == 0:
        STATUS_UPDATE_INTERVAL = 15
    else:
        STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)
    if len(task_dict) != 0 and (st := intervals["status"]):
        for key, intvl in list(st.items()):
            intvl.cancel()
            intervals["status"][key] = SetInterval(
                STATUS_UPDATE_INTERVAL, update_status_message, key
            )
    STATUS_LIMIT = environ.get("STATUS_LIMIT", "")
    STATUS_LIMIT = 4 if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)
    QUEUE_ALL = environ.get("QUEUE_ALL", "")
    QUEUE_ALL = "" if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)
    QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "")
    QUEUE_DOWNLOAD = "" if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)
    QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
    QUEUE_UPLOAD = "" if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)
    USER_SESSION_STRING = environ.get("USER_SESSION_STRING", "")
    CMD_SUFFIX = environ.get("CMD_SUFFIX", "")
    #DOWNLOAD
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
    if not INCOMPLETE_TASK_NOTIFIER and config_dict["DATABASE_URL"]:
        await database.trunc_table("tasks")
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
    USENET_SERVERS = environ.get("USENET_SERVERS", "")
    try:
        if len(USENET_SERVERS) == 0:
            USENET_SERVERS = []
        elif (us := eval(USENET_SERVERS)) and not us[0].get("host"):
            USENET_SERVERS = []
        else:
            USENET_SERVERS = eval(USENET_SERVERS)
    except Exception as e:
        LOGGER.error(f"Error loading usenet servers: {e}")
        USENET_SERVERS = []
    # Additional
    FILELION_API = environ.get("FILELION_API", "")
    if len(FILELION_API) == 0:
        FILELION_API = ""
    STREAMWISH_API = environ.get("STREAMWISH_API", "")
    if len(STREAMWISH_API) == 0:
        STREAMWISH_API = ""
    RSS_CHAT = environ.get("RSS_CHAT", "")
    RSS_CHAT = "" if len(RSS_CHAT) == 0 else RSS_CHAT
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

    config_dict.update(
        {
            'STATUS_UPDATE_INTERVAL': STATUS_UPDATE_INTERVAL,
            'STATUS_LIMIT': STATUS_LIMIT,
            'QUEUE_ALL': QUEUE_ALL,
            'QUEUE_DOWNLOAD': QUEUE_DOWNLOAD,
            'QUEUE_UPLOAD': QUEUE_UPLOAD,
            'USER_SESSION_STRING': USER_SESSION_STRING,
            'CMD_SUFFIX': CMD_SUFFIX,
            'BASE_URL': BASE_URL,
            'WEB_PINCODE': WEB_PINCODE,
            'INCOMPLETE_TASK_NOTIFIER': INCOMPLETE_TASK_NOTIFIER,
            'TORRENT_TIMEOUT': TORRENT_TIMEOUT,
            'USENET_SERVERS': USENET_SERVERS,
            'FILELION_API': FILELION_API,
            'STREAMWISH_API': STREAMWISH_API,
            'RSS_CHAT': RSS_CHAT,
            'RSS_DELAY': RSS_DELAY,
            'SEARCH_API_LINK': SEARCH_API_LINK,
            'SEARCH_LIMIT': SEARCH_LIMIT,
            'SEARCH_PLUGINS': SEARCH_PLUGINS
        }
    )
    await database.update_config()
    await gather(initiate_search_tools(), start_from_queued())
    add_job()


bot.add_handler(
    MessageHandler(
        bot_settings, filters=filters.command(BotCommands.BotSetCommand, case_sensitive=True) & CustomFilters.sudo
    )
)
bot.add_handler(
    CallbackQueryHandler(
        edit_bot_settings, filters=filters.regex("^botset") & CustomFilters.sudo
    )
)