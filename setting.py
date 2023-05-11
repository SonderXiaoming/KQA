from hoshino import R
import os
# ==================== ↓ 可修改的配置 ↓ ====================
'''
建议只修改配置，不删注释，不然以后会忘了怎么改还可以再看看
'''

# 储存数据位置（二选一，初次使用后不可改动，除非自己手动迁移，重启BOT生效，也可换成自己想要的路径）
FILE_PATH = R.img('kqa').path               # 数据在res文件夹里
IMG_PATH = os.path.join(FILE_PATH, 'img/')
# FILE_PATH = os.path.dirname(__file__)     # 数据在插件文件夹里

# 是否使用星乃自带的严格词库（二选一，可随时改动，重启BOT生效）
# USE_STRICT = True     # 使用星乃自带敏感词库，较为严格，安全可靠
USE_STRICT = False      # 使用KQA自带敏感词库，较为宽容，可自行增删

# 是否要启用消息分段发送，仅在查询问题时生效，避免消息过长发不出去（可随时改动，重启BOT生效）
IS_SPILT_MSG = True     # 是否要启用消息分段，默认开启，关闭改成False
MSG_LENTH = 1000        # 消息分段长度限制，只能数字，千万不能太小，默认1000
SPLIT_INTERVAL = 1      # 消息分段发送时间间隔，只能数字，单位秒，默认1秒

# 是否使用转发消息发送，仅在查询问题时生效，和上方消息分段可同时开启（可随时改动，重启BOT生效）
IS_FORWARD = False      # 开启后将使用转发消息发送，默认关闭

# 设置问答的时候，是否校验回答的长度，最大长度和上方 MSG_LENTH 保持一致（可随时改动，重启BOT生效）
IS_JUDGE_LENTH = False   # 校验回答的长度，在长度范围内就允许设置问题，超过就不允许，默认开启

# 如果开启分段发送，且长度没超限制，且开启转发消息时，由于未超长度限制只有一条消息，这时是否需要直接发送而非转发消息（可随时改动，重启BOT生效）
IS_DIRECT_SINGER = True  # 直接发送，默认开启

# 看问答的时候，展示的分隔符（可随时改动，重启BOT生效）
SPLIT_MSG = ' | '       # 默认' | '，可自行换成'\n'或者' '等。单引号不能漏

# ==================== ↑ 可修改的配置 ↑ ====================