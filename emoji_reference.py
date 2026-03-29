"""
表情回应快速参考

飞书支持的常用表情类型（emoji_type）
"""

# 正面/赞同
OK = "OK"
THUMBSUP = "THUMBSUP"           # 👍
THANKS = "THANKS"
MUSCLE = "MUSCLE"               # 💪
APPLAUSE = "APPLAUSE"           # 👏
DONE = "DONE"                   # ✅
LGTM = "LGTM"
OnIt = "OnIt"                   # 🎯
CheckMark = "CheckMark"
Yes = "Yes"

# 开心表情
SMILE = "SMILE"
LAUGH = "LAUGH"
LOL = "LOL"
LOVE = "LOVE"                   # ❤️
WINK = "WINK"
PROUD = "PROUD"
SMART = "SMART"                 # 🧠
JOYFUL = "JOYFUL"
WOW = "WOW"
YEAH = "YEAH"

# 中性/思考
THINKING = "THINKING"           # 💭
SILENT = "SILENT"               # 🤫
WHAT = "WHAT"
SHY = "SHY"
GLANCE = "GLANCE"               # 👀
EYESCLOSED = "EYESCLOSED"       # 😌

# 负面/悲伤
SOB = "SOB"
CRY = "CRY"
ERROR = "ERROR"                 # ❌
FACEPALM = "FACEPALM"
EMBARRASSED = "EMBARRASSED"
HEARTBROKEN = "HEARTBROKEN"

# 强烈情绪
ANGRY = "ANGRY"
SHOCKED = "SHOCKED"
TERROR = "TERROR"
SKULL = "SKULL"
SWEAT = "SWEAT"
SPEECHLESS = "SPEECHLESS"

# 疲惫/生病
SLEEP = "SLEEP"
DROWSY = "DROWSY"
YAWN = "YAWN"
SICK = "SICK"

# 动作/手势
WAVE = "WAVE"
HUG = "HUG"
CLAP = "CLAP"
PRAISE = "PRAISE"
HIGHFIVE = "HIGHFIVE"
ThumbsDown = "ThumbsDown"       # 👎

# 工作/状态
Typing = "Typing"               # ⌨️ 正在输入
StatusReading = "StatusReading" # 📖 阅读中
Get = "Get"
OneSecond = "OneSecond"
GeneralDoNotDisturb = "GeneralDoNotDisturb"
GeneralInMeetingBusy = "GeneralInMeetingBusy"
StatusInFlight = "StatusInFlight"
GeneralBusinessTrip = "GeneralBusinessTrip"
GeneralWorkFromHome = "GeneralWorkFromHome"
StatusEnjoyLife = "StatusEnjoyLife"

# 物品/符号
HEART = "HEART"                 # ❤️
ROSE = "ROSE"                   # 🌹
PARTY = "PARTY"                 # 🎉
BEER = "BEER"                   # 🍺
CAKE = "CAKE"                   # 🎂
GIFT = "GIFT"                   # 🎁
Coffee = "Coffee"               # ☕
Trophy = "Trophy"               # 🏆
Fire = "Fire"                   # 🔥
BOMB = "BOMB"                   # 💣
Music = "Music"                 # 🎵
Pin = "Pin"                     # 📌
Alarm = "Alarm"                 # ⏰
Loudspeaker = "Loudspeaker"     # 📢
CrossMark = "CrossMark"         # ❌
Hundred = "Hundred"             # 💯

# 使用示例
"""
from lark_oapi.api.im.v1 import *

# 添加表情回应
request = CreateMessageReactionRequest.builder() \
    .message_id(message_id) \
    .request_body(CreateMessageReactionRequestBody.builder()
        .reaction_type(ReactionType.builder()
            .emoji_type("THINKING")  # 使用上面的常量
            .build())
        .build()) \
    .build()

response = client.im.v1.message_reaction.create(request)

# 删除表情回应
request = DeleteMessageReactionRequest.builder() \
    .message_id(message_id) \
    .reaction_id(reaction_id) \
    .build()

response = client.im.v1.message_reaction.delete(request)
"""
