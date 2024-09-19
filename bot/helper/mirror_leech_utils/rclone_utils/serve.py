from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import create_subprocess_exec
from configparser import ConfigParser

from bot import rclone_options, CONFIG_DIR, LOCAL_DIR

RcloneServe = []

async def rclone_serve_booter():
    if RcloneServe:
        try:
            RcloneServe[0].kill()
            RcloneServe.clear()
        except:
            pass
    config = ConfigParser()
    if not await aiopath.exists(f"{CONFIG_DIR}/rclone.conf"):
        async with aiopen(f"{CONFIG_DIR}/rclone.conf", "w") as f:
            await f.write(rclone_options)
    else:
        async with aiopen("rclone.conf", "r") as f:
            contents = await f.read()
            config.read_string(contents)
    if not config.has_section("local"):
        config.add_section("local")
        config.set("local", "type", "alias")
        config.set("local", "remote", LOCAL_DIR)
    if not config.has_section("combine"):
        upstreams = " ".join(f"{remote}={remote}:" for remote in config.sections())
        config.add_section("combine")
        config.set("combine", "type", "combine")
        config.set("combine", "upstreams", upstreams)
        with open("rclone.conf", "w") as f:
            config.write(f, space_around_delimiters=False)
    cmd = [
        "rclone",
        "serve",
        "webdav",
        "--config",
        f"{CONFIG_DIR}/rclone.conf",
        "--no-modtime",
        "combine:",
        "--addr",
        f"{rclone_options['SERVE_ADRESS']}:{rclone_options['SERVE_PORT']}",
        "--vfs-cache-mode",
        "full",
        "--vfs-cache-max-age",
        "1m0s",
        "--buffer-size",
        "64M",
        "--user",
        rclone_options["SERVE_USER"],
        "--pass",
        rclone_options["SERVE_PASS"],
    ]
    rcs = await create_subprocess_exec(*cmd)
    RcloneServe.append(rcs)

async def rclone_serve_shutdown():
    if RcloneServe:
        try:
            RcloneServe[0].kill()
            RcloneServe.clear()
        except:
            pass
    return
