from sys import exit
from dotenv import load_dotenv
from logging import (
    FileHandler,
    StreamHandler,
    INFO,
    basicConfig,
    getLogger,
    ERROR,
)
from os import path, environ, remove, makedirs
import shutil
from subprocess import run as srun


if path.exists("log.txt"):
    remove("log.txt")
if path.exists("rlog.txt"):
    remove("rlog.txt")

basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)
getLogger("databases").setLevel(ERROR)
logger = getLogger(__name__)

if not path.exists('/usr/src/app/config'):
    makedirs('/usr/src/app/config')
if path.exists('/usr/src/app/config.env') and not path.exists('/usr/src/app/config/config.env'):
    shutil.copy('/usr/src/app/config.env', '/usr/src/app/config/config.env')
    
try:
    load_dotenv("config/config.env", override=True)
    if bool(environ.get("_____REMOVE_THIS_LINE_____")):
        raise Exception("The README.md file there to be read! Exiting now!")
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    OWNER_ID = environ.get("OWNER_ID", "")
    TELEGRAM_API = environ.get("TELEGRAM_API", "")
    TELEGRAM_HASH = environ.get("TELEGRAM_HASH", "")
    if not all([BOT_TOKEN, OWNER_ID, TELEGRAM_API, TELEGRAM_HASH]):
        raise Exception("Please fill the required fields in config.env file! Exiting now!")
except Exception as e:
    logger.error(f"Error occured while reading config.env file: {e}")
    exit(1)

UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "")
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = None

UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "")
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = "master"

if UPSTREAM_REPO is not None:
    if path.exists(".git"):
        srun(["rm", "-rf", ".git"])

    update = srun(
        [
            f"git init -q \
                     && git remote add origin {UPSTREAM_REPO} \
                     && git fetch origin -q \
                     && git reset --hard origin/{UPSTREAM_BRANCH} -q"
        ],
        shell=True,
    )

    if update.returncode == 0:
        logger.info("Successfully updated with latest commit from UPSTREAM_REPO")
    else:
        logger.error(
            "Something went wrong while updating, check UPSTREAM_REPO if valid or not!"
        )
