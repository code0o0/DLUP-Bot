from sys import exit
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aria2p import API as ariaAPI, Client as ariaClient
from asyncio import Lock, new_event_loop, set_event_loop
from dotenv import load_dotenv, dotenv_values
from logging import (
    getLogger,
    FileHandler,
    StreamHandler,
    INFO,
    basicConfig,
    ERROR,
)
import json
from shutil import rmtree
import secrets
from os import remove, path as ospath, environ, getcwd
from pyrogram import Client as TgClient, enums
from qbittorrentapi import Client as QbClient
from sabnzbdapi import SabnzbdClient
from socket import setdefaulttimeout
from sqlite3 import connect
from subprocess import Popen, run
from time import time
from tzlocal import get_localzone
from uvloop import install
install()
setdefaulttimeout(600)

basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)
LOGGER = getLogger(__name__)
getLogger("qbittorrentapi").setLevel(INFO)
getLogger("requests").setLevel(INFO)
getLogger("urllib3").setLevel(INFO)
getLogger("pyrogram").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)
getLogger("databases").setLevel(ERROR)

botStartTime = time()

BASE_URL_PORT = 9001
RC_PORT = 9002
FB_PORT = 9003
NZB_PORT = 9004
QB_PORT = 9005
DHT_PORT = 9006
LOCAL_DIR = '/usr/src/app/storage'
CONFIG_DIR = '/usr/src/app/config'
DOWNLOAD_DIR = '/usr/src/app/downloads'
DATABASE_URL = f'{CONFIG_DIR}/data.db'
CONFIG_PATH = f'{CONFIG_DIR}/config.env'

intervals = {"status": {}, "qb": "", "jd": "", "nzb": "", "stopAll": False}
qb_torrents = {}
jd_downloads = {}
nzb_jobs = {}
user_data = {}
aria2_options = {}
qbit_options = {}
nzb_options = {}
fb_options = {"user": "admins", "passwd": secrets.token_urlsafe(8), "enable": False}
jd_options = {"jd_email": "admins", "jd_passwd": secrets.token_urlsafe(8)}
rclone_options = {"user": "admins", "passwd": secrets.token_urlsafe(8), "enable": False}
queued_dl = {}
queued_up = {}
non_queued_dl = set()
non_queued_up = set()
multi_tags = set()
task_dict_lock = Lock()
queue_dict_lock = Lock()
qb_listener_lock = Lock()
nzb_listener_lock = Lock()
jd_lock = Lock()
cpu_eater_lock = Lock()
subprocess_lock = Lock()
same_directory_lock = Lock()
status_dict = {}
task_dict = {}
rss_dict = {}

run(
    f"mkdir -p {LOCAL_DIR} {DOWNLOAD_DIR} Thumbnails rclone tokens && chmod -R 755 {LOCAL_DIR} Thumbnails rclone tokens",
    shell=True,
)
load_dotenv(CONFIG_PATH, override=True)
BOT_TOKEN = environ.get("BOT_TOKEN", "")
if len(BOT_TOKEN) == 0:
    LOGGER.error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)
BOT_ID = BOT_TOKEN.split(":", 1)[0]

conn = connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
if cur.fetchone():
    cur.execute("SELECT * FROM settings WHERE _id = ?", (BOT_ID,))
    row = cur.fetchone()
    current_config = dict(dotenv_values(CONFIG_PATH))
    deploy_config = json.loads(row[1]) if row else None
    if deploy_config != current_config:
        deploy_config = current_config
    else:
        config_dict = json.loads(row[2])
        for key, value in config_dict.items():
            environ[key] = str(value)
    aria2_options = json.loads(row[3]) if row else {}
    qbit_options = json.loads(row[4]) if row else {}
    fb_options = json.loads(row[5]) if row else {}
    jd_options = json.loads(row[6]) if row else {}
    rclone_options = json.loads(row[7]) if row else {}
    LOGGER.info("Loaded settings from database")
else:
    deploy_config = dict(dotenv_values(CONFIG_PATH))
    LOGGER.info("Loaded settings from .env file")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
if cur.fetchone():
    cur.execute("SELECT * FROM files")
    rows = cur.fetchall()
    for row in rows:
        path = row[0]
        pf_bin = row[1]
        with open(path, "wb+") as f:
            f.write(pf_bin)
        if path.endswith(".zip"):
            _folder = path.split(".zip")[0]
            rmtree(_folder, ignore_errors=True)
            run(["7z", "x", path, f"-o{_folder}"])
            run(["chmod", "-R", "755", _folder])
            remove(path)
    LOGGER.info("Loaded files from database")
cur.close()
conn.close()

if ospath.exists("sabnzbd/SABnzbd.ini.bak"):
    remove("sabnzbd/SABnzbd.ini.bak")

if not ospath.exists(".netrc"):
    run("touch .netrc && chmod 600 .netrc && cp .netrc /root/.netrc", shell=True)

if not ospath.exists(f"{CONFIG_DIR}/filebrowser.db"):
    user = fb_options.get("user")
    passwd = fb_options.get("passwd")
    run(
        f"filebrowser config init --database {CONFIG_DIR}/filebrowser.db && " +
        f"filebrowser config import {getcwd()}/filebrowser/filebrowser.yaml --database {CONFIG_DIR}/filebrowser.db && " +
        f"filebrowser users add {user} {passwd} --database {CONFIG_DIR}/filebrowser.db  --perm.admin",
        shell=True,
    )
if fb_options.get("enable"):
    run(
        f"nohup filebrowser --database {CONFIG_DIR}/filebrowser.db > /dev/null 2>&1 &",
        shell=True,
    )

run(
    f"aria2c --conf-path={getcwd()}/aria2/aria2.conf -D && " +
    f"qbittorrent-nox -d --profile={getcwd()} && " +
    f"sabnzbdplus -f {getcwd()}/sabnzbd/SABnzbd.ini -s :::{NZB_PORT} -b 0 -d -c -l 0 --console",
    shell=True,
)

# REQUIRED CONFIG
BOT_TOKEN = environ.get("BOT_ID", "")
OWNER_ID = environ.get("OWNER_ID") if environ.get("OWNER_ID").digit() else 0
OWNER_ID = int(OWNER_ID)
TELEGRAM_API = environ.get("TELEGRAM_API") if environ.get("TELEGRAM_API").digit() else 0
TELEGRAM_API = int(TELEGRAM_API)
TELEGRAM_HASH = environ.get("TELEGRAM_HASH", "")
if not all([BOT_TOKEN, OWNER_ID, TELEGRAM_API, TELEGRAM_HASH]):
    LOGGER.error("Missing required environment variables! Exiting now")
    exit(1)
try:
    bot = TgClient(
        "bot",
        TELEGRAM_API,
        TELEGRAM_HASH,
        bot_token=BOT_TOKEN,
        parse_mode=enums.ParseMode.HTML,
        max_concurrent_transmissions=10,
    ).start()
    bot_name = bot.me.username
except Exception as e:
    LOGGER.error(f"Error creating bot client: {e}")
    exit(1)

#BOT
STATUS_UPDATE_INTERVAL = environ.get("STATUS_UPDATE_INTERVAL", "")
if len(STATUS_UPDATE_INTERVAL) == 0:
    STATUS_UPDATE_INTERVAL = 15
else:
    STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)
STATUS_LIMIT = environ.get("STATUS_LIMIT", "")
STATUS_LIMIT = 4 if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)
QUEUE_ALL = environ.get("QUEUE_ALL", "")
QUEUE_ALL = "" if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)
QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "")
QUEUE_DOWNLOAD = "" if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)
QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
QUEUE_UPLOAD = "" if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)
USER_SESSION_STRING = environ.get("USER_SESSION_STRING", "")
if len(USER_SESSION_STRING) != 0:
    LOGGER.info("Creating client from USER_SESSION_STRING")
    try:
        user = TgClient(
            "user",
            TELEGRAM_API,
            TELEGRAM_HASH,
            session_string=USER_SESSION_STRING,
            parse_mode=enums.ParseMode.HTML,
            max_concurrent_transmissions=10,
        ).start()
        IS_PREMIUM_USER = user.me.is_premium
    except Exception as e:
        LOGGER.error(f"Error creating user client: {e}")
        IS_PREMIUM_USER = False
        user = ""
else:
    IS_PREMIUM_USER = False
    user = ""
CMD_SUFFIX = environ.get("CMD_SUFFIX", "")

#DOWNLOAD
BASE_URL = environ.get("BASE_URL", "").rstrip("/")
if len(BASE_URL) == 0:
    LOGGER.warning("BASE_URL not provided!")
    BASE_URL = ""
else:
    Popen(
        f"gunicorn web.wserver:app --bind 0.0.0.0:{BASE_URL_PORT} --worker-class gevent",
        shell=True,
    )
WEB_PINCODE = environ.get("WEB_PINCODE", "")
WEB_PINCODE = WEB_PINCODE.lower() == "true"
INCOMPLETE_TASK_NOTIFIER = environ.get("INCOMPLETE_TASK_NOTIFIER", "")
INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == "true"
TORRENT_TIMEOUT = environ.get("TORRENT_TIMEOUT", "")
TORRENT_TIMEOUT = "" if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)
USENET_SERVERS = environ.get("USENET_SERVERS", "")
try:
    if len(USENET_SERVERS) == 0:
        USENET_SERVERS = []
    elif (us := eval(USENET_SERVERS)) and not us[0].get("host"):
        USENET_SERVERS = []
    else:
        USENET_SERVERS = eval(USENET_SERVERS)
except Exception as e:
    LOGGER.error(f"Wrong USENET_SERVERS format: {e}")
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
else:
    try:
        SEARCH_PLUGINS = eval(SEARCH_PLUGINS)
    except Exception as e:
        LOGGER.error(f"Wrong SEARCH_PLUGINS format: {e}")
        SEARCH_PLUGINS = ""

config_dict = {
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
    "USENET_SERVERS": USENET_SERVERS,
    'FILELION_API': FILELION_API,
    'STREAMWISH_API': STREAMWISH_API,
    'RSS_CHAT': RSS_CHAT,
    'RSS_DELAY': RSS_DELAY,
    'SEARCH_API_LINK': SEARCH_API_LINK,
    'SEARCH_LIMIT': SEARCH_LIMIT,
    'SEARCH_PLUGINS': SEARCH_PLUGINS,
    'LOCAL_DIR': LOCAL_DIR,
    'CONFIG_DIR': CONFIG_DIR,
    "DATABASE_URL": DATABASE_URL,
    "DOWNLOAD_DIR": DOWNLOAD_DIR,
}

qbittorrent_client = QbClient(
    host="localhost",
    port=QB_PORT,
    VERIFY_WEBUI_CERTIFICATE=False,
    REQUESTS_ARGS={"timeout": (30, 60)},
    HTTPADAPTER_ARGS={
        "pool_maxsize": 500,
        "max_retries": 10,
        "pool_block": True,
    },
)
sabnzbd_client = SabnzbdClient(
    host="http://localhost",
    api_key="mltb",
    port=str(NZB_PORT),
)
aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))

bot_loop = new_event_loop()
set_event_loop(bot_loop)
nzb_options = bot_loop.run_until_complete(sabnzbd_client.get_config())["config"]["misc"]
if not aria2_options:
    aria2_options.update(aria2.get_global_options())
else:
    aria2.set_global_options(aria2_options)
if not qbit_options:
    qbit_options = dict(qbittorrent_client.app_preferences())
    qbit_options = {k: v for k, v in qbit_options.items() if not k.startswith(("rss", "listen_port"))}
    qbit_options["web_ui_password"] = secrets.token_urlsafe(8)
    qbittorrent_client.app_set_preferences({"web_ui_password": passwd})
else:
    qb_opt = {**qbit_options}
    qbittorrent_client.app_set_preferences(qb_opt)

scheduler = AsyncIOScheduler(timezone=str(get_localzone()), event_loop=bot_loop)
