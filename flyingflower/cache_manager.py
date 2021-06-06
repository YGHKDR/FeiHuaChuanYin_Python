# -*- coding:utf-8 -*-
import logging
from typing import Any
import aioredis

from .settings import REDIS_HOST, REDIS_DB, REDIS_PORT
from .utils import pack, unpack
from .cache_build import CacheBuilder

_Logger = logging.getLogger()
PREFIX_CACHE = "ebrose_"
POETRY_CACHE_KEY = "cache_build_key"

async def connect():

    redis_addr = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    conn = await aioredis.create_redis_pool(redis_addr, db=int(REDIS_DB))
    return conn

cache = None


async def redis_set(key, value, expire=24*60*60):   #, expire=24*60*60
    global cache
    if not cache:
        cache = await connect()

    value = pack(value)      #把value用某种方式打包

    try:
        await cache.set(key, value, expire=expire)    #放入cache中  , expire=expire
    except Exception as e:
        _Logger.error(f"redis error when set {key} to {value}, err = ",e)
        return None
    return True


async def redis_get(key):
    global cache
    if not cache:
        cache = await connect()

    try:
        value = await cache.get(key)
        print(type(value))
    except Exception as err:
        print("错误1 %s" % err)
        return None

    return unpack(value)

                                                  #, timeout=24*60*60
async def set_user_cache(uid: str, value: Any, timeout=24*60*60):   #uid就是token  value是user_cache，包括token, pivot, processed, count  三个单引号/双引号定义一个字符串
    '''set user cache                            

    struct:
        {
            "pivot": "花",
            "processed": [1,2,3]
            "count": 0,
            "token": "x"
        }
    '''
    key = "%s%s"%(PREFIX_CACHE, uid)    #key是一串字符串ebrose_uid
    return await redis_set(key, value, timeout)  #, timeout


async def get_user_cache(uid):     #得到用户的缓存

    key = "%s%s"%(PREFIX_CACHE, uid)
    return await redis_get(key)


async def get_pivot_cache(pivot):   #得到令词的缓存

    key = POETRY_CACHE_KEY
    try:
        all_cache = await redis_get(key)   #cachebuilder.get_cache()
        print(all_cache)
        print(type(all_cache))
    except Exception as result:
        print("错误2=%s" % result)

    
    if pivot in all_cache:
        return all_cache[pivot]
    return []
