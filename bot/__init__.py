from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aria2p import API as ariaAPI, Client as ariaClient
from asyncio import Lock
from dotenv import load_dotenv, dotenv_values
from logging import (
    getLogger,
    FileHandler,
    StreamHandler,
    INFO,
    basicConfig,
    error as log_error,
    info as log_info,
    warning as log_warning,
    ERROR,
)
import json
from os import remove, path as ospath, environ, getcwd
from pyromod import Client as tgClient
from pyrogram import enums
from qbittorrentapi import Client as qbClient
from socket import setdefaulttimeout
from sqlite3 import connect
from subprocess import Popen, run
from time import time
from tzlocal import get_localzone
from uvloop import install

# from faulthandler import enable as faulthandler_enable
# faulthandler_enable()

install()
setdefaulttimeout(600)

getLogger("qbittorrentapi").setLevel(INFO)
getLogger("requests").setLevel(INFO)
getLogger("urllib3").setLevel(INFO)
getLogger("pyrogram").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)

botStartTime = time()

basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)
LOGGER = getLogger(__name__)

LOCAL_DIR = '/usr/src/app/storage'
CONFIG_DIR = '/usr/src/app/config'
DATABASE_URL = f'{CONFIG_DIR}/data.db'
DOWNLOAD_DIR = '/usr/src/app/downloads'

aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))
if not ospath.exists(f'{CONFIG_DIR}/dht.dat'):
    run(["touch", f"{CONFIG_DIR}/dht.dat"])
if not ospath.exists(f'{CONFIG_DIR}/dht6.dat'):
    run(["touch", f"{CONFIG_DIR}/dht6.dat"])

try:
    load_dotenv('config.env', override=True)
    if bool(environ.get("_____REMOVE_THIS_LINE_____")):
        log_error("The README.md file there to be read! Exiting now!")
        exit(1)
except:
    pass

Intervals = {"status": {}, "qb": "", "jd": ""}
QbTorrents = {}
jd_downloads = {}
DRIVES_NAMES = []
DRIVES_IDS = []
INDEX_URLS = []
GLOBAL_EXTENSION_FILTER = ["aria2", "!qB"]
user_data = {}
aria2_options = {}
qbit_options = {}
queued_dl = {}
queued_up = {}
non_queued_dl = set()
non_queued_up = set()
multi_tags = set()

task_dict_lock = Lock()
queue_dict_lock = Lock()
qb_listener_lock = Lock()
jd_lock = Lock()
cpu_eater_lock = Lock()
subprocess_lock = Lock()
status_dict = {}
task_dict = {}
rss_dict = {}

BOT_TOKEN = environ.get("BOT_TOKEN", "")
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)
bot_id = BOT_TOKEN.split(":", 1)[0]

conn = connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='config'")
if cur.fetchone():
    cur.execute("SELECT * FROM config WHERE _id = ?", (bot_id,))
    row = cur.fetchone()
    current_config = dict(dotenv_values("config.env"))
    deploy_config = json.loads(row[1]) if row else None
    if deploy_config != current_config:
        deploy_config = current_config
    else:
        config_dict = json.loads(row[2])
        for key, value in config_dict.items():
            environ[key] = str(value)
    pf_dict = json.loads(row[3]) if row else {}
    for key, value in pf_dict.items():
        with open(key, "wb+") as f:
            f.write(value)
        if key == "cfg.zip":
            run(["rm", "-rf", "/JDownloader/cfg"])
            run(["7z", "x", "cfg.zip", "-o/JDownloader"])
            remove("cfg.zip")
    aria2_options = json.loads(row[4]) if row else {}
    qbit_options = json.loads(row[5]) if row else {}
else:
    deploy_config = dict(dotenv_values("config.env"))
cur.close()
conn.close()

# REQUIRED CONFIG
OWNER_ID = environ.get("OWNER_ID", "")
if len(OWNER_ID) == 0:
    log_error("OWNER_ID variable is missing! Exiting now")
    exit(1)
else:
    OWNER_ID = int(OWNER_ID)
TELEGRAM_API = environ.get("TELEGRAM_API", "")
if len(TELEGRAM_API) == 0:
    log_error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)
else:
    TELEGRAM_API = int(TELEGRAM_API)
TELEGRAM_HASH = environ.get("TELEGRAM_HASH", "")
if len(TELEGRAM_HASH) == 0:
    log_error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)

#BOT
STATUS_UPDATE_INTERVAL = environ.get("STATUS_UPDATE_INTERVAL", "")
if len(STATUS_UPDATE_INTERVAL) == 0:
    STATUS_UPDATE_INTERVAL = 15
else:
    STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)
STATUS_LIMIT = environ.get("STATUS_LIMIT", "")
STATUS_LIMIT = 10 if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)
QUEUE_ALL = environ.get("QUEUE_ALL", "")
QUEUE_ALL = "" if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)
QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "")
QUEUE_DOWNLOAD = "" if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)
QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
QUEUE_UPLOAD = "" if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)
USER_SESSION_STRING = environ.get("USER_SESSION_STRING", "")
if len(USER_SESSION_STRING) != 0:
    log_info("Creating client from USER_SESSION_STRING")
    user = tgClient(
        "user",
        TELEGRAM_API,
        TELEGRAM_HASH,
        session_string=USER_SESSION_STRING,
        parse_mode=enums.ParseMode.HTML,
        max_concurrent_transmissions=10,
    ).start()
    IS_PREMIUM_USER = user.me.is_premium
else:
    IS_PREMIUM_USER = False
    user = ""
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
BASE_URL = environ.get("BASE_URL", "").rstrip("/")
if len(BASE_URL) == 0:
    log_warning("BASE_URL not provided!")
    BASE_URL = ""
WEB_PINCODE = environ.get("WEB_PINCODE", "")
WEB_PINCODE = WEB_PINCODE.lower() == "true"
INCOMPLETE_TASK_NOTIFIER = environ.get("INCOMPLETE_TASK_NOTIFIER", "")
INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == "true"
YT_DLP_OPTIONS = environ.get("YT_DLP_OPTIONS", "")
if len(YT_DLP_OPTIONS) == 0:
    YT_DLP_OPTIONS = ""
TORRENT_TIMEOUT = environ.get("TORRENT_TIMEOUT", "")
TORRENT_TIMEOUT = "" if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)

#UPLOAD
DEFAULT_UPLOAD = environ.get("DEFAULT_UPLOAD", "")
if DEFAULT_UPLOAD != "rc":
    DEFAULT_UPLOAD = "gd"
EXTENSION_FILTER = environ.get("EXTENSION_FILTER", "")
if len(EXTENSION_FILTER) > 0:
    fx = EXTENSION_FILTER.split()
    for x in fx:
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
if (
    len(LEECH_SPLIT_SIZE) == 0
    or int(LEECH_SPLIT_SIZE) > MAX_SPLIT_SIZE
    or LEECH_SPLIT_SIZE == "2097152000"
):
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

config_dict = {
    # BOT_TOKEN, OWNER_ID, TELEGRAM_API, TELEGRAM_HASH, AUTHORIZED_CHATS, SUDO_USERS
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
    'MAX_SPLIT_SIZE': MAX_SPLIT_SIZE,
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
    'SEARCH_PLUGINS': SEARCH_PLUGINS,
    'LOCAL_DIR': LOCAL_DIR,
    'CONFIG_DIR': CONFIG_DIR,
    "DATABASE_URL": DATABASE_URL,
    "DOWNLOAD_DIR": DOWNLOAD_DIR,
}

if GDRIVE_ID:
    DRIVES_NAMES.append("Main")
    DRIVES_IDS.append(GDRIVE_ID)
    INDEX_URLS.append(INDEX_URL)

if ospath.exists("list_drives.txt"):
    with open("list_drives.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            DRIVES_IDS.append(temp[1])
            DRIVES_NAMES.append(temp[0].replace("_", " "))
            if len(temp) > 2:
                INDEX_URLS.append(temp[2])
            else:
                INDEX_URLS.append("")

if BASE_URL:
    Popen(
        f"gunicorn web.wserver:app --bind 0.0.0.0:{BASE_URL_PORT} --worker-class gevent",
        shell=True,
    )
run(["qbittorrent-nox", "-d", f"--profile={getcwd()}"])

if not ospath.exists(".netrc"):
    run(["touch", ".netrc"])
run(
    "chmod 600 .netrc && cp .netrc /root/.netrc && chmod +x aria.sh && ./aria.sh",
    shell=True,
)

if ospath.exists("accounts.zip"):
    if ospath.exists("accounts"):
        run(["rm", "-rf", "accounts"])
    run(["7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json"])
    run(["chmod", "-R", "777", "accounts"])
    remove("accounts.zip")
if not ospath.exists("accounts"):
    config_dict["USE_SERVICE_ACCOUNTS"] = False


def get_client():
    return qbClient(
        host="localhost",
        port=8090,
        VERIFY_WEBUI_CERTIFICATE=False,
        REQUESTS_ARGS={"timeout": (30, 60)},
    )
qb_client = get_client()

qbit_edit_opts = ['dl_limit', 'up_limit', 'max_connec', 'max_connec_per_torrent', 'disk_cache', 'disk_cache_ttl',
                  'preallocate_all', 'max_seeding_time_enabled', 'max_seeding_time', 'max_ratio_enabled', 'max_ratio',
                  'dht', 'pex', 'lsd', 'encryption', 'anonymous_mode', 'proxy_type', 'proxy_peer_connections', 
                  'proxy_torrents_only', 'proxy_ip', 'proxy_port', 'proxy_auth_enabled', 'proxy_username',
                  'proxy_password']
aria2c_edit_opts = ['max-overall-download-limit', 'max-overall-upload-limit', 'max-download-limit', 'max-upload-limit',
                    'split', 'min-split-size', 'max-connection-per-server', 'disk-cache', 'file-allocation', 'user-agent',
                    'seed-ratio', 'seed-time', 'bt-max-peers', 'enable-dht', 'enable-dht6', 'bt-enable-lpd',
                    'enable-peer-exchange']
aria2c_global = ["bt-max-open-files", "download-result", "keep-unfinished-download-result", "log", "log-level",
                 "max-concurrent-downloads", "max-download-result", "max-overall-download-limit", "save-session",
                 "max-overall-upload-limit", "optimize-concurrent-downloads", "save-cookies", "server-stat-of"]

if not qbit_options:
    qbit_all_options = dict(qb_client.app_preferences())
    qbit_options = {key: qbit_all_options[key] for key in qbit_edit_opts}
else:
    qb_opt = {**qbit_options}
    for k, v in qb_opt.items():
        if v in ["", "*"]:
            del qb_opt[k]
    qb_client.app_set_preferences(qb_opt)

if not aria2_options:
    aria2_all_options = aria2.client.get_global_option()
    aria2_options = {key: aria2_all_options[key] for key in aria2c_edit_opts}
else:
    a2c_glo = {op: aria2_options[op] for op in aria2c_global if op in aria2_options}
    aria2.set_global_options(a2c_glo)

log_info("Creating client from BOT_TOKEN")
bot = tgClient(
    "bot",
    TELEGRAM_API,
    TELEGRAM_HASH,
    bot_token=BOT_TOKEN,
    workers=1000,
    parse_mode=enums.ParseMode.HTML,
    max_concurrent_transmissions=10,
).start()
bot_loop = bot.loop

scheduler = AsyncIOScheduler(timezone=str(get_localzone()), event_loop=bot_loop)
