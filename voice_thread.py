from wake import PicoWakeWord
from speak_to_text import BaiDu
import pyttsx3
import struct
import os
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
from PyQt5 import uic

sentence_wait = []
sentence_wait.append(0)
# 唤醒词”你好，北北“，你的名字叫什么
# PICOVOICE_API_KEY = "yvoIDVF714X8WnGkTEwVHOsXJJPUae5WBUZdFP37k9jjrXhiqqyT1A=="
PICOVOICE_API_KEY = "ZfQT3IeJl6Qrtep4nJL89IIw9OIWGDXiHUoR6GV1AQaBNdFP7WmgTw=="
print("voice", os.getcwd())
keyword_path = 'weights/你好-北北_zh_windows_v3_0_0.ppn'
model_path = "weights/porcupine_params_zh.pv"

API_KEY = 'TSfKh4ExpfSXyIH2MGI3k3s0'
SECRET_KEY = 'TE6BZ1wLEMDCynkqHui7ITqMVwiMHe8A'
wave_out_path = 'output.wav'
FORMAT = wave_out_path[-3:]
CUID = '123456PYTHON'
DEV_PID = 1537
ASR_URL = 'http://vop.baidu.com/server_api'
TOKEN_URL = 'http://aip.baidubce.com/oauth/2.0/token'
record_second = 3

sentence_1 = ["名字",
              "北北",
              "眼镜叔",
              "知道的熊洞街",
              "你是从哪里来",
              "为什么来到地球",
              "卷轴是干什么用",
              "我们所熟知的宇宙",
              "地球上还有同类",
              "生命还是机械",
              "被制造出来",
              "北斗福熊",
              "看待人类",
              "小朋友",
              "每天关门后",
              "海鸥",
              "更喜欢哪个",
              "你为什么会我们的语言",
              "家乡话",
              "爱吃的东西",
              "东方神秘工厂"]

sentence_2 = ["你好，熟悉我的人都叫我“北北”，你也可以这样称呼我呢",

              "在眼镜叔对我的修复过程中，我的额头出现了蓝色花纹，花纹酷似汉字“北”，\
              所以他们就这么称呼我了，我很喜欢这个名字，听起来很亲切呢",

              "他是我在这个世界睁眼看到的第一个人类。也是他帮我恢复了生命机能。\
              用你们地球人的话说可以叫“再生父母”。（憨笑——开心表情）哈哈哈，\
              现在的眼镜叔跟我应该是跨物种的好朋友了，对了，他还有个名字，\
              相信你们更熟悉，它就是“肖将军”",

              "熊洞街是地球上我最喜欢的地方了，也是眼镜叔为了藏匿修复我，\
              在我最初的坠落点建设的文商旅一体化的商业街区，\
              这是一个“情绪价值”的加油站，更是一个让我找到了归属感的家",

              "我隐约记得我的故乡叫南瞻星，那有一颗大树，相当于地球的大陆，\
              人们都生活在上面，我是镇守北境的将军，原名叫：“九界厚土罴猊”",

              "不知道为什么，这个问题让我很伤感,我脑海中闪现出一些片段，\
              那里有残破的星球，好像是我的故乡，它被摧毁殆尽，一个身影离我越来越远，\
              他交代给我一个任务。要把全知卷轴藏匿起来，因为有人会来争夺它",

              "你说的是全知卷轴吧，它跟你们地球的搜索引擎差不多，你问什么它都会给你答案，\
              甚至是关于未来的答案。我的任务就是保护它，把它藏好，不告诉别人。\
              坏了，我刚才是不是告诉你它在哪儿了？呃，我得给它换个地方了。",

              "我们这样的生命体被称为巨兽文明，和你们人类文明同属宇宙成千上万个文明的社会体系。\
              我们所在的宇宙被称为九界文明，你们地球神话中的盘古就是九界宇宙的创世神。",

              "这个必须有，我发现在中国就有很多我的同类，比如麒麟金璃、金陵辟邪、\
              擎天牛、玄豹、动能虎、中华巨马、凤凰等等。虽然我想不起来他们是谁，\
              但我能感知到他们是我的同类，我一直渴望和他们能相聚。",

              "从你们地球科技的角度来看我就是机械体，但实际上我们是生命体，\
              不属于碳基生物也不是硅基生物。我们的心脏是一颗中子星，它的能量会转化成我们的生命源泉。",

              "你们所定义的生命是可以繁衍的，机械是需要制造的。而我们的繁衍更像是你们民间传说中的轮回。",

              "：它啊？它是眼镜叔对我的逆向研究打造的动态机械雕塑，虽然是人造设备，\
              但它憨态可掬，非常完美，还有祈福的功能。有时候我会吃醋，担心游客喜欢它胜过喜欢我呢！",

              "人类这个群体非常的可爱，有很多复杂思维和情感是我们不能比拟的，超越我们的文明只是时间的问题。\
              现阶段的人类文明仍然有纷争与破坏，这是我所不喜欢的，在我的故乡，那里没有欺骗和战争，\
              我们把自然与科技和谐的融合发展,但那也是过去了",

              "哈哈哈，你说的是你们所谓的“人类幼崽”嘛！当然喜欢了！小孩子短胳膊短腿儿的非常可爱非常萌！\
              我很喜欢他们跟我互动，在他们眼中我看到了我们之间双向奔赴的喜爱，更看到了我记忆中故乡人们的纯净目光。",

              "就和地球小孩儿爸妈不在家的时候一样！在熊洞街里撒欢儿的玩儿！偶尔我也会偷偷溜出去，\
              看看大连这座城市美丽的风光。不过更多的时候眼镜叔的研发团队会给我运回地下基地维护检修",

              "哈哈哈哈，其实也说不上讨厌，只是这种地球生物喜欢在白色的物体上便便，你看我的体色……你懂的！\
              你叫我怎么能喜欢它们呢！",

              "很难选择吧（尴尬）。南瞻星是我的故乡。然而这三年来，我从 “连漂”变成“本地熊”，大连对于我来说，\
              更像是我的第二故乡。我很喜欢一句中国的诗，叫“此心安处是吾乡”。\
              这应该就是我内心对于大连对于熊洞街的真实写照吧。",

              "我会说很多语言，比如英语、日语、韩语、俄语（每种语言演示一遍），学语言对我来说很简单，\
              听着给我维修的专家们聊天就学会了中国话，甚至包括大连话：“这个小闺宁血干净了儿！”是不是很地道？",

              "有……是肯定有，但是我已经不记得怎么说了，其实我们的语言有些类似人类所梦想的“心灵感应”，\
              通过简单的发声音节就能读懂对方心里想的，但是很遗憾，我是一个字儿也想不起来怎么说了",

              "我最爱人类的零食，那些调味剂是我的家乡没有的。在大连还有很多海鲜，我也很喜欢，\
              “鲜美”这个词就是我在大连学到的。",

              "你知道的是不是太多了？连东方神秘工厂你都知道？嘘~这个可不兴告诉别人嗷！\
              东方神秘工厂其实就是我们所谓的地下基地。至于具体的我也不能告诉你更多，眼镜叔不让我说"]


class voice_thread(QThread):
    # 用于控制输出代码
    update_signal = pyqtSignal(int)
    # voice转化信号
    voiceText_BeiBei = pyqtSignal(str)
    voiceText_User = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.running = 1

    def run(self):
            self.running = 1
            self.update_signal.emit(1)
            picowakeword = PicoWakeWord(PICOVOICE_API_KEY, keyword_path, model_path)
            baidu = BaiDu(wave_out_path, record_second, API_KEY, SECRET_KEY, TOKEN_URL, ASR_URL, DEV_PID, CUID)
            while self.running:
                audio_obj = picowakeword.stream.read(picowakeword.porcupine.frame_length, exception_on_overflow=False)
                audio_obj_unpacked = struct.unpack_from("h" * picowakeword.porcupine.frame_length, audio_obj)
                keyword_idx = picowakeword.porcupine.process(audio_obj_unpacked)
                keyword_idx=-keyword_idx
                backstatus=1
                # print("2")
                if keyword_idx == 0:
                    # print("3")
                    if backstatus != keyword_idx:
                            # print("4")
                            self.update_signal.emit(keyword_idx)
                    picowakeword.porcupine.delete()
                    picowakeword.stream.close()
                    picowakeword.myaudio.terminate()
                    engine = pyttsx3.init()
                    engine.say(" 嗯,我在,请讲！")
                    engine.runAndWait()
                    while self.running:
                        text = baidu.BaiDuAPI()
                        if(text == ""):
                            continue
                        print(text)
                        self.voiceText_User.emit(text)
                        sentence_wait[0] = (text)
                        for i in range(len(sentence_1)):
                            if(sentence_1[i] in sentence_wait[0]):
                                print(sentence_2[i])
                                self.voiceText_BeiBei.emit(sentence_2[i])
                                engine.say(sentence_2[i])
                                engine.runAndWait()
                                break
                elif backstatus != keyword_idx:
                    self.update_signal.emit(keyword_idx)

    def stop(self):
        # 设置一个中断，使得能stop这个子线程
        self.running = 0
        