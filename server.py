#-*- coding:utf-8 -*-

import logging
import asyncio

from dotenv import load_dotenv
load_dotenv(verbose=True)

from sanic import Sanic

from flyingflower.views import asr_view, tts_view, pivot_view
from flyingflower.settings import EBROSE_LOGGER_CONFIG
from flyingflower.cache_build import CacheBuilder

# 设置 log 
logging.config.dictConfig(EBROSE_LOGGER_CONFIG)

app = Sanic(name='flyingflower_public')
app.add_route(asr_view, '/ebrose/asr', methods=["GET"])
app.add_route(tts_view, '/ebrose/tts', methods=["GET"])
app.add_route(pivot_view, '/ebrose/pivot', methods=["GET"])

cachebuilder = CacheBuilder()
asyncio.ensure_future(cachebuilder.runner())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8000") 
# 启动定时任务
#启动服务之后，启动定时任务，把词表和句词联表（每个令词随机取出1000条数据）定期刷新到缓存中，客户端通过不同的路由访问不同方法