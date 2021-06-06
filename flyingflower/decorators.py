# -*- coding:utf-8 -*-
import re
import logging
import asyncio
from functools import wraps
from uuid import uuid4

from sanic import response

from .cache_manager import set_user_cache, get_user_cache
from .settings import SELECTED_WORDS
from flyingflower.cache_build import CacheBuilder

CHINESE_RE_PAT = re.compile(r"[\u4e00-\u9fa5]")
_Logger = logging.getLogger()


def set_token(coro):
    @wraps(coro)
    async def wrapper(request, *args, **kw):

        pivot = request.args.get("pivot")      #获得令词
        if len(pivot) != 1 or (not re.match(CHINESE_RE_PAT, pivot)):
            return response.json(
                {
                    "status": False,
                    "msg": "主题词输入错误",
                }
            )
        if not pivot in SELECTED_WORDS:
            return response.json(
                {
                  
                    "status": False,
                    "msg": "主题词仅包括{}".format(SELECTED_WORDS),
                }
            )

        new_token = str(uuid4())   #uuid生成一个独一无二的ID来标记对象
        user_cache = {
            "token": new_token,
            "pivot": pivot,
            "processed": [],
            "count": 0
        }
        await set_user_cache(new_token, user_cache)     #设置缓存
        return await coro(request, user_cache)          #在cache_manager.py中通过set_user_cache（）方法的redis_set（）设置
    return wrapper


def check_token(coro):               #检查是否有token这一独一无二的标记，如果有token，通过token获取到user_cache
    @wraps(coro)
    async def wrapper(request, *args, **kw):

        token = request.args.get("token") or request.form.get("token")
        if not token:
            return response.json(
                {
                    "msg": "未找到该用户",
                    "status": False
                }
            )

        user_cache = await get_user_cache(token)    #在cache_manager.py中通过get_user_cache（）方法的redis_get（）获取
        if not user_cache:
            return response.json(
                {
                    "msg": "未找到该用户",
                    "status": False
                }
            )

        return await coro(request, user_cache, *args, **kw)
    return wrapper