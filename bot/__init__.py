from sys import exit
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aria2p import API as ariaAPI, Client as ariaClient
from asyncio import Lock, get_running_loop, new_event_loop, set_event_loop
from convopyro import Conversation
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
from shutil import rmtree
from os import remove, path as ospath, environ
from pyrogram import Client as TgClient, enums
from qbittorrentapi import Client as QbClient
from sabnzbdapi import SabnzbdClient
from socket import setdefaulttimeout
from sqlite3 import connect
from subprocess import Popen, run
from time import time
from tzlocal import get_localzone
from uvloop import install
from concurrent.futures import ThreadPoolExecutor


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

try:
    bot_loop = get_running_loop()
except RuntimeError:
    bot_loop = new_event_loop()
    set_event_loop(bot_loop)

THREADPOOL = ThreadPoolExecutor(max_workers=99999)
bot_loop.set_default_executor(THREADPOOL)

basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)
LOGGER = getLogger(__name__)

LOCAL_DIR = '/usr/src/app/Storage'
CONFIG_DIR = '/usr/src/app/config'
DATABASE_URL = f'{CONFIG_DIR}/data.db'
DOWNLOAD_DIR = '/usr/src/app/downloads'
for dir in [LOCAL_DIR, CONFIG_DIR, DOWNLOAD_DIR, "Thumbnails", "rclone", "tokens"]:
    if not ospath.exists(dir):
        run(["mkdir", "-p", dir])

try:
    load_dotenv('config.env', override=True)
    if bool(environ.get("_____REMOVE_THIS_LINE_____")):
        log_error("The README.md file there to be read! Exiting now!")
        exit(1)
except:
    pass

intervals = {"status": {}, "qb": "", "jd": "", "nzb": "", "stopAll": False}
QbTorrents = {}
jd_downloads = {}
nzb_jobs = {}
drives_names = []
drives_ids = []
index_urls = []
global_extension_filter = ["aria2", "!qB"]
user_data = {}
aria2_options = {}
qbit_options = {}
nzb_options = {}
rclone_options = {}
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
status_dict = {}
task_dict = {}
rss_dict = {}

BOT_TOKEN = environ.get("BOT_TOKEN", "")
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)
BOT_ID = BOT_TOKEN.split(":", 1)[0]

conn = connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
if cur.fetchone():
    cur.execute("SELECT * FROM settings WHERE _id = ?", (BOT_ID,))
    row = cur.fetchone()
    current_config = dict(dotenv_values("config.env"))
    deploy_config = json.loads(row[1]) if row else None
    if deploy_config != current_config:
        deploy_config = current_config
    else:
        config_dict = json.loads(row[2])
        for key, value in config_dict.items():
            environ[key] = str(value)
    aria2_options = json.loads(row[3]) if row else {}
    qbit_options = json.loads(row[4]) if row else {}
    rclone_options = json.loads(row[5]) if row else {}
else:
    deploy_config = dict(dotenv_values("config.env"))

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
if cur.fetchone():
    cur.execute("SELECT * FROM files")
    rows = cur.fetchall()
    for row in rows:
        path = row[0]
        pf_bin = json.loads(row[1])
        with open(path, "wb+") as f:
            f.write(pf_bin)
cur.close()
conn.close()

if ospath.exists("sabnzbd/SABnzbd.ini.bak"):
    remove("sabnzbd/SABnzbd.ini.bak")
if ospath.exists("cfg.zip"):
    rmtree("/JDownloader/cfg")
    run(["7z", "x", "cfg.zip", "-o/JDownloader"])
    remove("cfg.zip")
if ospath.exists("accounts.zip"):
    if ospath.exists("accounts"):
        rmtree("accounts")
    run(["7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json"])
    run(["chmod", "-R", "777", "accounts"])
    remove("accounts.zip")
if not ospath.exists(".netrc"):
    run(["touch", ".netrc"])
if not ospath.exists(f'{CONFIG_DIR}/dht.dat'):
    run(["touch", f"{CONFIG_DIR}/dht.dat"])
if not ospath.exists(f'{CONFIG_DIR}/dht6.dat'):
    run(["touch", f"{CONFIG_DIR}/dht6.dat"])
run(
    "chmod 600 .netrc && cp .netrc /root/.netrc && chmod +x aria-nox-nzb.sh && ./aria-nox-nzb.sh",
    shell=True,
)

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
STATUS_LIMIT = 4 if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)
QUEUE_ALL = environ.get("QUEUE_ALL", "")
QUEUE_ALL = "" if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)
QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "")
QUEUE_DOWNLOAD = "" if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)
QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
QUEUE_UPLOAD = "" if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)
USER_SESSION_STRING = environ.get("USER_SESSION_STRING", "")
if len(USER_SESSION_STRING) != 0:
    log_info("Creating client from USER_SESSION_STRING")
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
    except:
        log_error("Failed to start client from USER_SESSION_STRING")
        IS_PREMIUM_USER = False
        user = ""
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
else:
    Popen(
        f"gunicorn web.wserver:app --bind 0.0.0.0:{BASE_URL_PORT} --worker-class gevent",
        shell=True,
    )
WEB_PINCODE = environ.get("WEB_PINCODE", "")
WEB_PINCODE = WEB_PINCODE.lower() == "true"
INCOMPLETE_TASK_NOTIFIER = environ.get("INCOMPLETE_TASK_NOTIFIER", "")
INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == "true"
YT_DLP_OPTIONS = environ.get("YT_DLP_OPTIONS", "")
if len(YT_DLP_OPTIONS) == 0:
    YT_DLP_OPTIONS = ""
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
except:
    log_error(f"Wrong USENET_SERVERS format: {USENET_SERVERS}")
    USENET_SERVERS = []

#UPLOAD
DEFAULT_UPLOAD = environ.get("DEFAULT_UPLOAD", "")
if DEFAULT_UPLOAD != "rc":
    DEFAULT_UPLOAD = "gd"
EXTENSION_FILTER = environ.get("EXTENSION_FILTER", "")
if len(EXTENSION_FILTER) > 0:
    fx = EXTENSION_FILTER.split()
    for x in fx:
        x = x.lstrip(".")
        global_extension_filter.append(x.strip().lower())
USE_SERVICE_ACCOUNTS = environ.get("USE_SERVICE_ACCOUNTS", "")
USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == "true"
NAME_SUBSTITUTE = environ.get("NAME_SUBSTITUTE", "")
NAME_SUBSTITUTE = "" if len(NAME_SUBSTITUTE) == 0 else NAME_SUBSTITUTE
if not ospath.exists("accounts"):
    USE_SERVICE_ACCOUNTS = False

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
if GDRIVE_ID:
    drives_names.append("Main")
    drives_ids.append(GDRIVE_ID)
    index_urls.append(INDEX_URL)
if ospath.exists("list_drives.txt"):
    with open("list_drives.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            drives_ids.append(temp[1])
            drives_names.append(temp[0].replace("_", " "))
            if len(temp) > 2:
                index_urls.append(temp[2])
            else:
                index_urls.append("")

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
MIXED_LEECH = environ.get("MIXED_LEECH", "")
MIXED_LEECH = MIXED_LEECH.lower() == "true" and IS_PREMIUM_USER

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
else:
    try:
        SEARCH_PLUGINS = eval(SEARCH_PLUGINS)
    except:
        log_error(f"Wrong USENET_SERVERS format: {SEARCH_PLUGINS}")
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
    "USENET_SERVERS": USENET_SERVERS,
    'DEFAULT_UPLOAD': DEFAULT_UPLOAD,
    'EXTENSION_FILTER': EXTENSION_FILTER,
    'USE_SERVICE_ACCOUNTS': USE_SERVICE_ACCOUNTS,
    "NAME_SUBSTITUTE": NAME_SUBSTITUTE,
    'GDRIVE_ID': GDRIVE_ID,
    'STOP_DUPLICATE': STOP_DUPLICATE,
    'IS_TEAM_DRIVE': IS_TEAM_DRIVE,
    'INDEX_URL': INDEX_URL,
    'LEECH_SPLIT_SIZE': LEECH_SPLIT_SIZE,
    'AS_DOCUMENT': AS_DOCUMENT,
    'EQUAL_SPLITS': EQUAL_SPLITS,
    'MEDIA_GROUP': MEDIA_GROUP,
    'USER_TRANSMISSION': USER_TRANSMISSION,
    'LEECH_FILENAME_PREFIX': LEECH_FILENAME_PREFIX,
    'LEECH_DUMP_CHAT': LEECH_DUMP_CHAT,
    'MIXED_LEECH': MIXED_LEECH,
    'JD_EMAIL': JD_EMAIL,
    'JD_PASS': JD_PASS,
    'FILELION_API': FILELION_API,
    'STREAMWISH_API': STREAMWISH_API,
    'RSS_CHAT': RSS_CHAT,
    'RSS_DELAY': RSS_DELAY,
    'SEARCH_API_LINK': SEARCH_API_LINK,
    'SEARCH_LIMIT': SEARCH_LIMIT,
    'SEARCH_PLUGINS': SEARCH_PLUGINS,
    'MAX_SPLIT_SIZE': MAX_SPLIT_SIZE,
    'LOCAL_DIR': LOCAL_DIR,
    'CONFIG_DIR': CONFIG_DIR,
    "DATABASE_URL": DATABASE_URL,
    "DOWNLOAD_DIR": DOWNLOAD_DIR,
}

qbittorrent_client = QbClient(
    host="localhost",
    port=8090,
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
    port="8070",
)

aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))

log_info("Creating client from BOT_TOKEN")
app = TgClient(
    "bot",
    TELEGRAM_API,
    TELEGRAM_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML,
    max_concurrent_transmissions=10,
)
Conversation(app)
bot = app.start()
bot_name = bot.me.username

scheduler = AsyncIOScheduler(timezone=str(get_localzone()), event_loop=bot_loop)


def get_qb_options(sync=False):
    if not qbit_options or sync:
        qbit_options.update(dict(qbittorrent_client.app_preferences()))
        del qbit_options["listen_port"]
        for k in list(qbit_options.keys()):
            if k.startswith("rss"):
                del qbit_options[k]
        if qbit_options.get("web_ui_password") != "mltbmltb":
            qbittorrent_client.app_set_preferences({"web_ui_password": "mltbmltb"})
    else:
        qb_opt = {**qbit_options}
        qbittorrent_client.app_set_preferences(qb_opt)


aria2c_edit_opts = ['max-overall-download-limit', 'max-overall-upload-limit', 'max-download-limit', 'max-upload-limit',
                    'split', 'min-split-size', 'max-connection-per-server', 'disk-cache', 'file-allocation', 'user-agent',
                    'seed-ratio', 'seed-time', 'bt-max-peers', 'enable-dht', 'enable-dht6', 'bt-enable-lpd',
                    'enable-peer-exchange']
aria2c_global = ["bt-max-open-files", "download-result", "keep-unfinished-download-result", "log", "log-level",
                 "max-concurrent-downloads", "max-download-result", "max-overall-download-limit", "save-session",
                 "max-overall-upload-limit", "optimize-concurrent-downloads", "save-cookies", "server-stat-of"]
def get_aria2_options():
    if not aria2_options:
        aria2_all_options = aria2.client.get_global_option()
        aria2_options.update({key: aria2_all_options[key] for key in aria2c_edit_opts})
    else:
        a2c_glo = {op: aria2_options[op] for op in aria2c_global if op in aria2_options}
        aria2.set_global_options(a2c_glo)

async def get_nzb_options():
    nzb_options.update((await sabnzbd_client.get_config())["config"]["misc"])

if not rclone_options:
    rclone_options = {
        "SERVE_ADRESS": "",
        "SERVE_PORT": 20002,
        "SERVE_USER": "admin",
        "SERVE_PASS": "password0",
    }


get_qb_options()
get_aria2_options()
bot_loop.run_until_complete(get_nzb_options())
