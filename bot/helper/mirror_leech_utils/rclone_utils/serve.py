from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import create_subprocess_exec
from configparser import ConfigParser

from bot import RC_PORT, LOCAL_DIR, LOGGER, rclone_options

RcloneServe = []

async def rclone_serve_booter():
    if RcloneServe:
        try:
            RcloneServe[0].kill()
            RcloneServe.clear()
        except Exception as e:
            LOGGER.error(f"Error in killing rclone serve: {e}")
    if not await aiopath.exists("rclone.conf"):
        await (await create_subprocess_exec("touch", "rclone.conf")).wait()
    config = ConfigParser()
    async with aiopen("rclone.conf", "r") as f:
        contents = await f.read()
        config.read_string(contents)
    if not config.has_section("local"):
        if config.has_section("combine"):
            config.remove_section("combine")
        config.add_section("local")
        config.set("local", "type", "alias")
        config.set("local", "remote", LOCAL_DIR)
    if not config.has_section("combine"):
        upstreams = " ".join(f"{remote}={remote}:" for remote in config.sections())
        config.add_section("combine")
        config.set("combine", "type", "combine")
        config.set("combine", "upstreams", upstreams)
        async with aiopen("rclone.conf", "w") as f:
            config.write(f, space_around_delimiters=False)
    cmd = [
        "rclone",
        "serve",
        "webdav",
        "--config",
        "rclone.conf",
        "--no-modtime",
        "combine:",
        "--addr",
        f"[::]:{RC_PORT}",
        "--vfs-cache-mode",
        "full",
        "--vfs-cache-max-age",
        "1m0s",
        "--buffer-size",
        "64M",
        "--user",
        rclone_options["user"],
        "--pass",
        rclone_options["passwd"],
    ]
    rcs = await create_subprocess_exec(*cmd)
    RcloneServe.append(rcs)

async def rclone_serve_shutdown():
    if RcloneServe:
        try:
            RcloneServe[0].kill()
            RcloneServe.clear()
        except Exception as e:
            LOGGER.error(f"Error in killing rclone serve: {e}")
    return
