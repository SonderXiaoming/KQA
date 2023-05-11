import html
import re
from typing import Tuple
from hoshino.typing import HoshinoBot
from .util import adjust_list, adjust_img, delete_img, spilt_msg, QuestionCache
from .database.dal import question_sqla

# 保存问答
async def set_que(bot:HoshinoBot, group_id: str, user_id: str, que_raw: str, ans_raw: str) -> str:
    # html转码
    que_raw = html.unescape(que_raw)
    ans_raw = html.unescape(ans_raw)
    # 新问题就调整并下载图片
    que_raw = await adjust_img(bot, que_raw, save=True)
    # 保存新的回答
    ans_raw = await adjust_img(bot, ans_raw, save=True)
    ans = ans_raw.split('#')
    ans = await adjust_list(ans, '#')
    # 已有问答再次设置的话，就先删除旧图片
    ans_old = QuestionCache.get_questions(group_id, user_id).get(que_raw, [])
    if ans_old:
        await delete_img(ans_old)
        await question_sqla.update_question(group_id, user_id, que_raw, str(ans))
    else:
        await question_sqla.insert_question({"group_id": group_id, "user_id": user_id, "question": que_raw, "answer": str(ans)})
    QuestionCache.add_question(group_id, user_id, que_raw, ans)
    return '好的我记住了'


# 显示有人/我问 和 查其他人的问答
async def show_que(group_id: str, user_id: str, search_str: str, msg_head: str) -> list:
    search_str = html.unescape(search_str)
    # 对象
    object = '管理员' if user_id == 'all' else '你'
    # 查询问题列表
    question_list = list(QuestionCache.get_questions(group_id, user_id))
    if search_str:
        search_list = []
        for question in question_list:
            if re.search(rf'\S*{search_str}\S*', question):
                search_list.append(question)
        question_list = search_list

    # 获取消息列表
    if not question_list:
        result_list = [f'{msg_head}{"本群中" if group_id != "all" else ""}没有找到任何{object}设置的问题呢']
    else:
        result_list = spilt_msg(question_list, f'{msg_head}{object}在群里设置的问题有：\n')
    return result_list

# 删除问答

async def del_que(bot:HoshinoBot, group_id: str, user_id: str, unque_str: str) -> Tuple[str]:
    unque_str = html.unescape(unque_str)
    ans = QuestionCache.get_questions(group_id, user_id).get(unque_str)
    if ans:
        ans_str = '#'.join(ans)  # 调整图片
        ans_str = await adjust_img(bot, ans_str, is_ans=True)
        QuestionCache.del_question(group_id, user_id, unque_str)
        await question_sqla.delete_question(group_id, user_id, unque_str)
        return f'我不再回答 “{ans_str}” 了', ans  # 返回输出文件以及需要删除的图片
    else:
        return "没有找到该问题", []
