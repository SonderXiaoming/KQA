import ast
import base64
import os
import re
import random
from typing import Dict, List, Optional
import urllib
import asyncio
import httpx
from hoshino.typing import CQEvent, HoshinoBot
from hoshino import logger, util
from .database.model import Question
from .textfilter.filter import DFAFilter
from .database.dal import question_sqla
from .setting import *

#答案中的图片换成b64
async def ans_img2b64(ans:str):
    cq_list : List[List[str]]= re.findall(r'\[CQ:image,file=file:///(\S+)\]', ans)
    for cqcode in cq_list:
        ans = ans.replace(f"file:///{cqcode}", f'base64://{base64.b64encode(open(cqcode,"rb").read()).decode()}')
    return ans

async def download(url:str, filename:str):
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as response:
            with open(filename, 'wb') as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
# 匹配替换字符
async def replace_message(match_que: re.Match, match_dict: dict, que: str) -> str:
    ans_tmp = match_dict.get(que)
    # 随机选择
    ans = random.choice(ans_tmp)
    flow_num = re.search(r'\S*\$([0-9])\S*', ans)
    if not flow_num:
        return ans
    for i in range(int(flow_num.group(1))):
        ans = ans.replace(f'${i + 1}', match_que.group(i + 1))
    return ans


# 调整转义分割字符 “#”
async def adjust_list(list_tmp: List[str], char: str) -> list:
    ans_list = []
    str_tmp = list_tmp[0]
    i = 0
    while i < len(list_tmp):
        if list_tmp[i].endswith('\\'):
            str_tmp += char + list_tmp[i + 1]
        else:
            ans_list.append(str_tmp)
            str_tmp = list_tmp[i + 1] if i + 1 < len(list_tmp) else list_tmp[i]
        i += 1
    return ans_list


# 下载以及分类图片
async def doing_img(bot, img: str, is_ans: bool = False, save: bool = False) -> str:
    if save:
        try:
            img_url = await bot.get_image(file=img)
            file = os.path.join(IMG_PATH, img)
            if not os.path.isfile(IMG_PATH + img):
                await download(img_url['url'], file)
                logger.critical(f'KQA: 已下载图片{img}')
        except:
            if not os.path.isfile(IMG_PATH + img):
                logger.critical(f'KQA: 图片{img}已经过期，请重新设置问答')
            pass
    if is_ans:  # 保证保存图片的完整性，方便迁移和后续做操作
        return 'file:///' + os.path.abspath(IMG_PATH + img)
    return img


# 进行图片处理
async def adjust_img(bot, str_raw: str, is_ans: bool = False, save: bool = False) -> str:
    flit_msg = beautiful(str_raw)  # 整个消息匹配敏感词
    cq_list : List[List[str]]= re.findall(r'(\[CQ:(\S+?),(\S+?)=(\S+?)])', str_raw)  # 找出其中所有的CQ码
    # 对每个CQ码元组进行操作
    for cqcode in cq_list:
        flit_cq = beautiful(cqcode[0])  # 对当前的CQ码匹配敏感词
        raw_body = cqcode[3].split(',')[0].split('.image')[0].split('/')[-1].split('\\')[-1]  # 获取等号后面的东西，并排除目录
        if cqcode[1] == 'image':
            # 对图片单独保存图片，并修改图片路径为真实路径
            raw_body = raw_body if '.' in raw_body else raw_body + '.image'
            raw_body = await doing_img(bot, raw_body, is_ans, save)
        if is_ans:
            # 如果是回答的时候，就将 匹配过的消息 中的 匹配过的CQ码 替换成未匹配的
            flit_msg = flit_msg.replace(
                flit_cq, f'[CQ:{cqcode[1]},{cqcode[2]}={raw_body}]')
        else:
            # 如果是保存问答的时候，就只替换图片的路径，其他CQ码的替换相当于没变
            str_raw = str_raw.replace(
                cqcode[0], f'[CQ:{cqcode[1]},{cqcode[2]}={raw_body}]')
    # 解决回答中不用于随机回答的\#
    flit_msg = flit_msg.replace('\#', '#')
    return str_raw if not is_ans else flit_msg

# 删啊删
async def delete_img(list_raw: list) -> list:
    for str_raw in list_raw:
        img_list = re.findall(r'(\[CQ:image,file=(.+?\.image)\])', str_raw)
        for img in img_list:
            file = img[1]
            try:
                file = os.path.split(file)[-1]
            except:
                pass
            try:
                os.remove(os.path.abspath(FILE_PATH + '/img/' + img[1]))
                logger.info(f'KQA: 已删除图片{file}')
            except:
                logger.info(f'KQA: 图片{file}不存在，无需删除')


# 和谐模块
def beautifulworld(msg: str) -> str:
    w = ''
    infolist = msg.split('[')
    for i in infolist:
        if i:
            try:
                w = w + '[' + i.split(']')[0] + ']' + \
                    beautiful(i.split(']')[1])
            except:
                w = w + beautiful(i)
    return w


# 切换和谐词库
def beautiful(msg: str) -> str:
    beautiful_message = DFAFilter()
    beautiful_message.parse(os.path.join(os.path.dirname(
        __file__), 'textfilter', 'sensitive_words.txt'))
    if USE_STRICT:
        msg = util.filt_message(msg)
    else:
        msg = beautiful_message.filter(msg)
    return msg


# 消息分段 | 输入：问题列表 和 初始的前缀消息内容 | 返回：需要发送的完整消息列表（不分段列表里就一个）
def spilt_msg(msg_list: list, init_msg: str) -> list:
    result_list = []
    # 未开启长度限制
    if not IS_SPILT_MSG:
        logger.info('KQA未开启长度限制')
        result_list.append(init_msg + SPLIT_MSG.join(msg_list))
        return result_list

    # 开启了长度限制
    logger.info(f'KQA已开启长度限制，长度限制{MSG_LENTH}')
    lenth = len(init_msg)
    tmp_list = []
    for msg_tmp in msg_list:
        if msg_list.index(msg_tmp) == 0:
            msg_tmp = init_msg + msg_tmp
        lenth += len(msg_tmp)
        # 判断如果加上当前消息后会不会超过字符串限制
        if lenth < MSG_LENTH:
            tmp_list.append(msg_tmp)
        else:
            result_list.append(SPLIT_MSG.join(tmp_list))
            # 长度和列表置位
            tmp_list = [msg_tmp]
            lenth = len(msg_tmp)
    result_list.append(SPLIT_MSG.join(tmp_list))
    return result_list

# 发送消息函数


async def send_result_msg(bot:HoshinoBot, ev:CQEvent, result_list):
    # 未开启转发消息
    if not IS_FORWARD:
        logger.info('KQA未开启转发消息，将循环分时直接发送')
        # 循环发送
        for msg in result_list:
            await bot.send(ev, msg)
            await asyncio.sleep(SPLIT_INTERVAL)
        return

    # 开启了转发消息但总共就一条消息，且 IS_DIRECT_SINGER = True
    if IS_DIRECT_SINGER and len(result_list) == 1:
        logger.info('KQA已开启转发消息，但总共就一条消息，将直接发送')
        await bot.send(ev, result_list[0])
        return

    # 开启了转发消息
    logger.info('KQA已开启转发消息，将以转发消息形式发送')
    forward_list = []
    for result in result_list:
        data = {
            "type": "node",
            "data": {
                "name": "神秘的环奈",
                "uin": 1791800364,
                "content": result
            }
        }
        forward_list.append(data)
    await bot.send_group_forward_msg(group_id=ev['group_id'], messages=forward_list)

def get_question_key(ev:CQEvent, que_type):
    return str(ev.group_id) if que_type != '全群' else "all", str(ev.user_id) if que_type not in ["全群", "有人"] else "all"

class QuestionCache:
    question_dict = {"all": {"all": {}}}

    @staticmethod
    async def init():
        question_dict = QuestionCache.question_dict
        questions: List[Question] = await question_sqla.query_question()
        for question in questions:
            if question.group_id not in question_dict:
                question_dict[question.group_id] = {"all": {}}
            if question.user_id not in question_dict[question.group_id]:
                question_dict[question.group_id][question.user_id] = {}
            question_dict[question.group_id][question.user_id][question.question] = ast.literal_eval(question.answer)

    @staticmethod
    async def _match(info: Dict[str, dict], cmd: str) -> Optional[List[str]]:
        ans = ""
        # 优先完全匹配
        if cmd in info:
            return random.choice(info[cmd])
        # 其次正则匹配
        for que in info:
            try:
                cq_list = re.findall(r'\[(CQ:(\S+?),(\S+?)=(\S+?))\]', que)  # 找出其中所有的CQ码
                que_new = que
                for cq_msg in cq_list:
                    que_new = que_new.replace(cq_msg[0], '\[' + cq_msg[1] + '\]')
                if re.match(que_new + '$', cmd):
                    ans = await replace_message(re.match(que_new + '$', cmd), info, que)
                    break
            except re.error:
                # 如果que不是re.pattern的形式就跳过
                continue
        return ans

    @staticmethod
    async def match(cmd: str, group_id: str, user_id: str) -> Optional[List[str]]:
        question_dict = QuestionCache.question_dict
        group_dict = question_dict.get(group_id, {'all': {}})
        if not (ans := await QuestionCache._match(group_dict.get(user_id, {}), cmd)):
            if not (ans := await QuestionCache._match(group_dict['all'], cmd)):
                ans = await QuestionCache._match(question_dict["all"]["all"], cmd)
        return ans
    
    @staticmethod
    def get_questions(group_id:str, user_id:str) -> Dict[str, List[str]]:
        return QuestionCache.question_dict.get(group_id, {'all': {}}).get(user_id, {})
    
    @staticmethod
    def add_question(group_id:str, user_id:str, question:str, answer:List[str]):
        question_dict = QuestionCache.question_dict
        if group_id not in question_dict:
            question_dict[group_id] = {'all': {}}
        if user_id not in question_dict[group_id]:
            question_dict[group_id][user_id] = {}
        question_dict[group_id][user_id][question] = answer
    
    @staticmethod
    def del_question(group_id:str, user_id:str, question:str):
        del QuestionCache.question_dict[group_id][user_id][question]
