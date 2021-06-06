#-*- coding:utf-8 -*-
from logging import getLogger
import traceback
import random
import re

from sanic.log import logger as _Logger
from sanic import response
from sanic.request import Request

from .decorators import check_token, set_token
from .utils import aip_asr, aip_tts, split_sentence
from .db_manager1 import get_sentence_by_text, get_sentence_by_id, get_poetry_by_id
from .cache_manager import set_user_cache, get_pivot_cache
from .cache_build import CacheBuilder

_Logger = getLogger(__name__)

class Ret:
    # success code -> 0xx 
    # err code
    #   1xx session 
    #   2xx asr 
    #   3xx tts
    SUCCESS_CODE = 0
    EMPTY_ASR_AUDIO = 201
    BAIDU_ASR_ERR = 202
    INVALID_PIVOT_ERR = 101
    UNLOGIN_ERR = 102
    FAIL_NOT_VALID_SENTENCE = 103
    FAIL_REPEATED = 104
    FAIL_LOSE = 105
    FAIL_PARAMS_ERROR = 106
    SYS_AUDIO_ERR = 301
    UNHANDLED_ERR = 400

    POETRY_CACHE_KEY = "cache_build_key"

@check_token                 
async def asr_view(request, user_cache):                     #该方法主要是当用户说诗句传入后端时，识别该诗句是否有令词，该诗句是否存在，若都有，则登记
    # 解包相关信息，供之后逻辑调用`                             #从user_cache获取token, pivot, processed_id等信息
    token, pivot = user_cache["token"], user_cache["pivot"]   #从request.file获取语音信息，然后对语音进行判断
    processed_id = user_cache["processed"]


    sentence=request.args.get("sentence")    #改：直接传sentence过来
    #return response.text(sentence)
    sentence = split_sentence(sentence, pivot)                  #用pivot来判断sentence中是否有令词，若无，返回json信息
    _Logger.debug(f"get asr sentence = {sentence}")
    if not sentence:
        resp = {"msg":f"需要说含有{pivot}的诗句哦", 
                "ret": Ret.FAIL_NOT_VALID_SENTENCE, 
                "status": False,
                "data": {
                    "author": "",
                    "title": "",
                    "text": ""
                    }
                }

        return response.json(resp)

    result = await get_sentence_by_text(sentence)             #如果sentence中有令词，那么通过文字返回该sentence的信息，判断sentence是否是诗句
    _Logger.debug(f"mysql search result = {result}")          #如果sentence是诗句，那么返回相关id信息
    if not result:
        resp = {"msg":"没听过这句诗哦", 
                "ret": Ret.FAIL_NOT_VALID_SENTENCE, 
                "status": False,
                "data": {
                    "author": "",
                    "title": "",
                    "text": ""
                    }
                }

        return response.json(resp)

    sent_id, poetry_id, _ = result        #通过运行sql语句得到id, poetry_id, text
    sent_id = int(sent_id)                #如果processed_id中有id，则已经说过；如果没有则加上
    if sent_id in processed_id:
        resp = {
            "msg": "这句已经说过了",
            "ret": Ret.FAIL_REPEATED,
            "status": False,
            "data": {
                "author": "",
                "title": "",
                "text": ""
                    }
        }
        return response.json(resp)

    user_cache["processed"].append(sent_id)
    user_cache["count"] += 1
    await set_user_cache(token, user_cache)       #修改后再设置入cache中    
    author, title, poetry_text = await get_poetry_by_id(poetry_id)        
    _Logger.debug(f"get poetry from sql text = {poetry_text}, author = {author}, {title}")
    return response.json(                         #返回这些信息到前端
        {
            "status": True,
            "ret": Ret.SUCCESS_CODE,
            "msg":"",
            "data": {
                "author": author,
                "title": title,
                "text": poetry_text
            }
        }
    )



@check_token
async def tts_view(request: Request, user_cache: dict):   #该方法是机器在准备返回下一句诗词的内容，判断该诗句有没有被说过、

    # 解包相关信息，供之后逻辑调用
    token, pivot = user_cache["token"], user_cache["pivot"]
    processed_id = user_cache["processed"]
    _Logger.debug(f"tts view token = {token} processed_id = {processed_id}")
    # 获取当前的缓存中的关于 pivot 的诗句
    sent_ids = await get_pivot_cache(pivot)
    sent_ids = [int(i) for i in sent_ids]
    random.shuffle(sent_ids)
    ans_id = None
    for _id in sent_ids:
        if _id not in processed_id:       #已经用过的诗句在processed_id中有记录
            ans_id = _id
            break

    if not ans_id:                        #如果全都轮流试一遍，没有还未尝试的id，则返回json
        return response.json(
            {
                "status": False,
                "ret": Ret.FAIL_LOSE,
                "msg": "当前刷新的id已经全部在 processed id 中",
                "data": {
                    "author": "",
                    "title": "",
                    "text": ""
                    }
            }
        )
                                                           #得到下一句的id
    _id, poetry_id, sentence_text = await get_sentence_by_id(ans_id)   #根据id从sentence表中查询语句  #报错

    user_cache["processed"].append(_id)
    await set_user_cache(token, user_cache)

    author, title, poetry_text = await get_poetry_by_id(poetry_id)
    _Logger.debug(f"get poetry from sql text = {poetry_text}, author = {author}, {title}")
    return response.json(                                  #返回机器需要返回的下一句的信息
        {
            "status": True,
            "ret": Ret.SUCCESS_CODE,
            "msg":sentence_text,
            "data": {
                "author": author,
                "title": title,
                "text": poetry_text
            }
        }
    )


@set_token
async def pivot_view(request: Request, user_cache:dict):      #当得到一个新的令词时，设置好关于这个令词的user_cache，然后从user_cache中得到token，传回前端
    _Logger.info("in pivot")                                  #user_cache是从decorators.py的set_token()中来   
    new_token = user_cache["token"]
    return response.json({
        "token": new_token,
        "msg": "记录成功",
        "ret": Ret.SUCCESS_CODE,
        "status": True,
    })
    
    

