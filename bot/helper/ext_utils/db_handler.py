from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, makedirs
from databases import Database
import json

from bot import (
    DATABASE_URL,
    user_data,
    rss_dict,
    LOGGER,
    bot_id,
    config_dict,
    aria2_options,
    qbit_options,
    bot_loop,
)


class DbManager:
    def __init__(self):
        self.__db = Database(f'sqlite+aiosqlite:///{DATABASE_URL}')
    
    async def db_init(self):
        query1 = "CREATE TABLE IF NOT EXISTS settings (_id TEXT, config_dict TEXT, \
            pf_dict TEXT DEFAULT '{}', aria2_options TEXT, qbit_options TEXT)"
        query2 = "CREATE TABLE IF NOT EXISTS users (_id INTEGER, user_dict TEXT)"
        query3 = "CREATE TABLE IF NOT EXISTS files (_id TEXT, pf_bin BLOB, user_id INTEGER)"
        query4 = "CREATE TABLE IF NOT EXISTS rss (_id INTEGER, user_rss TEXT)"
        query5 = "CREATE TABLE IF NOT EXISTS tasks (_id TEXT, cid INTEGER, tag TEXT)"
        async with self.__db:
            await self.__db.execute(query1)
            await self.__db.execute(query2)
            await self.__db.execute(query3)
            await self.__db.execute(query4)
            await self.__db.execute(query5)
    
    async def db_load(self):
        await self.db_init()
        _config_dict = json.dumps(config_dict)
        _aria2_options = json.dumps(aria2_options)
        _qbit_options = json.dumps(qbit_options)
        async with self.__db.transaction():
            row = await self.__db.fetch_one(query='SELECT * FROM settings WHERE _id = :id', values={'id': bot_id})
            if not row:
                query = 'INSERT INTO settings (_id, config_dict, aria2_options, qbit_options) \
                    VALUES (:id, :config_dict, :aria2_options, :qbit_options)'
                values = {'id': bot_id, 'config_dict': _config_dict, 'aria2_options': _aria2_options, 
                          'qbit_options': _qbit_options}
                await self.__db.execute(query=query, values=values)
        async with self.__db.transaction():
            if await self.__db.fetch_one(query='SELECT * from users'):
                # return a dict ==> {_id, is_sudo, is_auth, as_doc, thumb, yt_opt, media_group, equal_splits, split_size, rclone, rclone_path, token_pickle, gdrive_id, leech_dest, lperfix, lprefix, excluded_extensions, user_transmission, index_url, default_upload}
                async for row in self.__db.iterate(query='SELECT * from users'):
                    uid = row[0]
                    row = json.loads(row[1])
                    user_data[uid] = row
                LOGGER.info("Users data has been imported from Database")
        async with self.__db.transaction():
            if not await aiopath.exists("Thumbnails"):
                await makedirs("Thumbnails")
            if not await aiopath.exists("rclone"):
                await makedirs("rclone")
            if not await aiopath.exists("tokens"):
                await makedirs("tokens")
            if await self.__db.fetch_one(query='SELECT * from files'):
                async for row in self.__db.iterate(query='SELECT * from files'):
                    path = row[0]
                    pf_bin = json.loads(row[1])
                    async with aiopen(path, "wb") as pf:
                        await pf.write(pf_bin)
                LOGGER.info("Files data has been imported from Database")
        async with self.__db.transaction():
            if await self.__db.fetch_one(query='SELECT * from rss'):
                async for row in self.__db.iterate(query='SELECT * from rss'):
                    user_id = row[0]
                    row = json.loads(row[1])
                    rss_dict[user_id] = row
                LOGGER.info("Rss data has been imported from Database.")
    
    async def update_config(self, dict_):
        _config_dict = json.dumps(config_dict)
        async with self.__db.transaction():
            # row = await self.__db.fetch_one(query='SELECT * FROM settings WHERE _id = :id', values={'id': bot_id})
            # query = 'INSERT INTO settings (_id, config_dict) VALUES (:id, :config_dict)'
            # values = {'id': bot_id, 'config_dict': _config_dict}
            # await self.__db.execute(query=query, values=values)
            query = 'UPDATE settings SET config_dict = :config_dict  WHERE _id = :id'
            values = {'id': bot_id, 'config_dict': _config_dict}
            await self.__db.execute(query=query, values=values)
    
    async def update_aria2(self, key, value):
        _aria2_options = json.dumps(aria2_options)
        async with self.__db.transaction():
            query = 'UPDATE settings SET aria2_options = :aria2_options  WHERE _id = :id'
            values = {'id': bot_id, 'aria2_options': _aria2_options}
            await self.__db.execute(query=query, values=values)
    
    async def update_qbittorrent(self, key, value):
        _qbit_options = json.dumps(qbit_options)
        async with self.__db.transaction():
            query = 'UPDATE settings SET qbit_options = :qbit_options  WHERE _id = :id'
            values = {'id': bot_id, 'qbit_options': _qbit_options}
            await self.__db.execute(query=query, values=values)

    async def update_private_file(self, path):
        if await aiopath.exists(path):
            async with aiopen(path, "rb+") as pf:
                pf_bin = await pf.read()
        else:
            pf_bin = ""
        async with self.__db.transaction():
            row = await self.__db.fetch_one(query='SELECT * FROM settings WHERE _id = :id', values={'id': bot_id})
            _pf_dict = json.loads(row[3]) if row else {}
            if pf_bin:
                _pf_dict.update({path: pf_bin})
            elif _pf_dict.get(path):
                del _pf_dict[path]
            else:
                return
            _pf_dict = json.dumps(_pf_dict)
            query = 'UPDATE settings SET pf_dict = :pf_dict  WHERE _id = :id'
            values = {'id': bot_id, 'pf_dict': _pf_dict}
            await self.__db.execute(query=query, values=values)

    async def update_user_data(self, user_id):
        data = user_data.get(user_id, {})
        async with self.__db.transaction():
            if not data:
                await self.__db.execute(query='DELETE FROM users WHERE _id = :id', values={'id': user_id})
                await self.__db.execute(query='DELETE FROM files WHERE user_id = :id', values={'id': user_id})
                await self.__db.execute(query='DELETE FROM rss WHERE _id = :id', values={'id': user_id})
                return
            _data = json.dumps(data)
            row = await self.__db.fetch_one(query='SELECT * FROM users WHERE _id = :id', values={'id': user_id})
            if not row:
                query = 'INSERT INTO users (_id, user_dict) VALUES (:id, :user_dict)'
                values = {'id': user_id, 'user_dict': _data}
                await self.__db.execute(query=query, values=values)
            else:
                query = 'UPDATE users SET user_dict = :user_dict  WHERE _id = :id'
                values = {'id': user_id, 'user_dict': _data}
                await self.__db.execute(query=query, values=values)
    
    async def update_user_doc(self, user_id, key, path=""):
        if path:
            async with aiopen(path, "rb+") as doc:
                doc_bin = await doc.read()
        else:
            doc_bin = ""
        async with self.__db.transaction():
            if not doc_bin:
                await self.__db.execute(query="DELETE FROM files WHERE _id = :id", values={'id': path})
                return
            row = await self.__db.fetch_one(query='SELECT * FROM files WHERE _id = :id', values={'id': user_id})
            if not row:
                query = 'INSERT INTO files (_id, pf_bin, user_id) VALUES (:id, :pf_bin, :user_id)'
                values = {'id': path, 'pf_bin': doc_bin, 'user_id': user_id}
                await self.__db.execute(query=query, values=values)
            else:
                query = 'UPDATE files SET pf_bin = :pf_bin  WHERE _id = :id'
                values = {'id': path, 'pf_bin': doc_bin}
                await self.__db.execute(query=query, values=values)
    
    async def rss_update_all(self):
        async with self.__db.transaction():
            await self.__db.execute(query='DELETE FROM rss')
            query = 'INSERT INTO rss (_id, user_rss) VALUES (:id, :user_rss)'
            values = [{'id': user_id, 'user_rss': json.dumps(user_rss)} \
                      for user_id, user_rss in rss_dict.items()]
            await self.__db.execute_many(query=query, values=values)
    
    async def rss_update(self, user_id):
        async with self.__db.transaction():
            user_rss = rss_dict[user_id]
            user_rss = json.dumps(user_rss)
            row = await self.__db.fetch_one(query='SELECT * FROM rss WHERE _id = :id', values={'id': user_id})
            if not row:
                query = 'INSERT INTO rss (_id, user_rss) VALUES (:id, :user_rss)'
                values = {'id': user_id, 'user_rss': user_rss}
                await self.__db.execute(query=query, values=values)
            else:
                query = 'UPDATE rss SET user_rss = :user_rss  WHERE _id = :id'
                values = {'id': user_id, 'user_rss': user_rss}
                await self.__db.execute(query=query, values=values)
    
    async def rss_delete(self, user_id):
        async with self.__db.transaction():
            await self.__db.execute(query='DELETE FROM rss WHERE _id = :id', values={'id': user_id})
    
    async def add_incomplete_task(self, cid, link, tag):
        async with self.__db.transaction():
            query = 'INSERT INTO tasks (_id, cid, tag) VALUES (:id, :cid, :tag)'
            await self.__db.execute(query=query, values={'id': link, 'cid': cid, 'tag': tag})
    
    async def rm_complete_task(self, link):
        async with self.__db.transaction():
            await self.__db.execute(query='DELETE FROM tasks WHERE _id = :id', values={'id': link})
    
    async def get_incomplete_tasks(self):
        notifier_dict = {}
        async with self.__db.transaction():
            if await self.__db.fetch_one(query='SELECT * FROM tasks'):
                async for row in self.__db.iterate(query='SELECT * FROM tasks'):
                    if row[1] in list(notifier_dict.keys()):
                        if row[2] in list(notifier_dict[row[1]]):
                            notifier_dict[row[1]][row[2]].append(row[0])
                        else:
                            notifier_dict[row[1]][row[2]] = [row[0]]
                    else:
                        notifier_dict[row[1]] = {row[2] : [row[0]]}
            await self.__db.execute(query='DELETE FROM tasks')
        return notifier_dict
    
    async def trunc_table(self, name):
        async with self.__db.transaction():
            await self.__db.execute(query=f'DELETE FROM {name}')

if DATABASE_URL:
    bot_loop.run_until_complete(DbManager().db_load())
