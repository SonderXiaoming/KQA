'''
作者：SonderXiaoming

版本：1.0.0

KQA：支持正则，支持回流，支持随机回答，支持图片等CQ码的你问我答
'''

import re
import html
import os
from .database.dal import question_sqla
from .operate_msg import set_que, show_que, del_que
from .util import adjust_img, get_question_key, delete_img, send_result_msg, MSG_LENTH, IS_JUDGE_LENTH, QuestionCache, ans_img2b64
from hoshino import Service, priv
from hoshino.typing import HoshinoBot, CQEvent
from nonebot import on_startup
from hoshino.tool import anti_conflict
sv_help = '''
=====注意=====

可多行匹配，可匹配图片等

回答可以用'#'分割回答，可以随机回复这几个回答,'\#'将不会分割

支持正则表达式，请用英文括号分组，回流用$加数字

正则例子：我问(.{0,19})我(.{0,19})你答$1优衣酱$2

然后发送：抱着我可爱的自己

bot就会回复：抱着优衣酱可爱的自己

=====================

[我问A你答B] 设置个人问题

[有人问C你答D] 群管理员设置本群的有人问

[看看有人问] 看本群设置的有人问

[看看有人问X] 搜索本群设置的有人问，X为搜索内容

[看看我问] 看自己设置的问题

[看看我问Y] 搜索自己设置的问题，Y为搜索内容

[查问答@某人] 限群管理单独查某人的全部问答

[查问答@某人G] 限群管理单独查某人的问答，G为搜索内容

[不要回答H] 删除某个回答H，优先删除我问其次有人问

[@某人不要回答H] 限群管理删除某人的某个回答H
'''.strip()

sv = Service('KQA', enable_on_default=True, help_=sv_help)

# 帮助界面
@sv.on_fullmatch('问答帮助')
async def help(bot:HoshinoBot, ev:CQEvent):
    await bot.send(ev, sv_help)

# 搜索某个成员的问题和回答，限群管理员
@sv.on_prefix('查问答')
async def search_question(bot:HoshinoBot, ev:CQEvent):
    if priv.get_user_priv(ev) < priv.ADMIN:
        await bot.send(ev, f'搜索某个成员的问答只能群管理操作呢。个人查询问答请使用“看看我问”+搜索内容')
        return
    search_str = ev.message.extract_plain_text().strip()
    user_id = str(ev.user_id)
    if ev.message[0].type == 'at':
        if ev.message[0].data['qq'] != 'all':
            user_id = str(ev.message[0].data['qq'])
    group_id = str(ev.group_id)
    msg_init = f'QQ({user_id})的查询结果：\n'
    msg_head = f'查询"{search_str}"相关的结果如下：\n' if search_str else ''
    result_list = await show_que(group_id, user_id, search_str, msg_init + msg_head)
    # 发送消息
    await send_result_msg(bot, ev, result_list)

# 回复问答
@sv.on_message('group')
@anti_conflict
async def kqa(bot:HoshinoBot, ev:CQEvent):
    search = re.match(r'^看看(有人|我|全群)问([\s\S]*)$', str(ev.message))
    if search:
        que_type, search_str = search.group(1), search.group(2)
        group_id, user_id = get_question_key(ev, que_type)
        msg_head = f'查询"{search_str}"相关的结果如下：\n' if search_str else ''
        result_list = await show_que(group_id, user_id, search_str, msg_head)
        # 发送消息
        await send_result_msg(bot, ev, result_list)
        return
    
    results = re.match(r'^(全群|有人|我)问([\s\S]*)你答([\s\S]*)$', str(ev.message))
    if results:
        que_type, que_raw, ans_raw = results.group(1), results.group(2), results.group(3)
        if IS_JUDGE_LENTH and len(ans_raw) > MSG_LENTH:
            await bot.send(ev, f'回答的长度超过最大字符限制，限制{MSG_LENTH}字符，包括符号和图片转码，您设置的回答字符长度为[{len(ans_raw)}]')
            return
        group_id, user_id = get_question_key(ev, que_type)

        if group_id == "all" and priv.get_user_priv(ev) < priv.SUPERUSER:
            await bot.send(ev, f'全群问只能维护组设置呢')
            return

        if user_id == "all" and priv.get_user_priv(ev) < priv.ADMIN:
            await bot.send(ev, f'有人问只能群管理设置呢')
            return
        
        msg = await set_que(bot, group_id, user_id, que_raw, ans_raw)
        await bot.send(ev, msg)
        return
    
    unque_match = re.match(r'^(\[CQ:at,qq=[0-9]+\])? ?(全群)?不要回答([\s\S]*)$', str(ev.message))
    if unque_match: 
        is_all, unque_str = unque_match.group(2), unque_match.group(3)
        group_id, user_id = get_question_key(ev, "全群" if is_all else "我")
        if ev.message[0].type == 'at':
            if ev.message[0].data['qq'] != 'all':
                user_id = str(ev.message[0].data['qq'])

        if group_id == "all" and priv.get_user_priv(ev) < priv.SUPERUSER:
            await bot.send(ev, f'只有维护组可以删除所有群设置的有人问')
            return
        if user_id != str(ev.user_id) and priv.get_user_priv(ev) < priv.ADMIN:
            await bot.send(ev, f'删除他人问答仅限群管理员呢')
            return
        
        unque_str = await adjust_img(bot, unque_str)
        msg, del_image = await del_que(bot, group_id, user_id, unque_str)
        await bot.send(ev, msg)
        await delete_img(del_image)
        return
    
    group_id, user_id, message = str(ev.group_id), str(ev.user_id), str(ev.message)
    # 仅调整问题中的图片
    message = await adjust_img(bot, html.unescape(message))
    # 没有自己的问答才回复有人问
    if ans:= await QuestionCache.match(message, group_id, user_id):
        ans = await adjust_img(bot, ans, is_ans=True, save=True)
        ans = await ans_img2b64(ans)
        await bot.send(ev, ans)

# 添加敏感词
@sv.on_prefix('KQA添加敏感词')
async def add_sensitive_words(bot:HoshinoBot, ev:CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        await bot.send(ev, f'该功能限维护组')
        return
    info = ev.message.extract_plain_text().strip()
    infolist = info.split(' ')
    for i in infolist:
        file = os.path.join(os.path.dirname(__file__), 'textfilter/sensitive_words.txt')
        with open(file, 'a+', encoding='utf-8') as f:
            f.write(i + '\n')
    await bot.send(ev, f'添加完毕')

# 删除敏感词
@sv.on_prefix('KQA删除敏感词')
async def del_sensitive_words(bot:HoshinoBot, ev:CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        await bot.send(ev, f'该功能限维护组')
        return
    info = ev.message.extract_plain_text().strip()
    infolist = info.split(' ')
    for i in infolist:
        file = os.path.join(os.path.dirname(__file__), 'textfilter/sensitive_words.txt')
        with open(file, "r", encoding='utf-8') as f:
            lines = f.readlines()
        with open(file, "w", encoding='utf-8') as f:
            for line in lines:
                if line.strip("\n") != i:
                    f.write(line)
    await bot.send(ev, f'删除完毕')

@on_startup
async def init_question():
    await question_sqla.create_all()
    await QuestionCache.init()