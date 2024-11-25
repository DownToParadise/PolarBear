from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
from PyQt5 import uic
import torch
from cameraV2 import videoProcessingThread
from voice_thread import voice_thread
import time
from ctypes import create_string_buffer
from camera_controlV1 import Camera

# 登录界面
class Login(QWidget):
    switch_window = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("/home/yeung/code/mmaction2-main/qt2/login.ui")
        #登录界面ui控件
        self.ip_line = self.ui.ip_line
        self.admin_line = self.ui.admin_line
        self.pw_line = self.ui.pw_line
        self.login_button = self.ui.login_button
        #连接槽
        self.login_button.clicked.connect(self.switchwindow)

    def switchwindow(self):
        self.switch_window.emit()
        # print('哈哈')


class PlatForm(QMainWindow):
    # 线程生命区
    videoThread = videoProcessingThread()
    #语音线程
    voicethread=voice_thread()

    # 信号
    detectSignal = pyqtSignal(bool)
    trackSignal = pyqtSignal(bool)
    targetID = pyqtSignal(object)

    def __init__(self):
        super(PlatForm, self).__init__()
        self.ui = uic.loadUi("/home/yeung/code/mmaction2-main/qt2/platform.ui")

        # 获取ui控件
        #视觉控件
        self.detectedVideo = self.ui.video
        self.detectButton = self.ui.detectButton
        self.textBrowser = self.ui.textBrowser
        self.lineEdit = self.ui.lineEdit
        self.trackButton = self.ui.trackButton
        # 语音控件
        self.voice_enable_button = self.ui.voice_enable
        self.voice_disable_button = self.ui.voice_disable
        self.textBrowser = self.ui.textBrowser

        # 发送信号
        self.detectSignal.connect(self.videoThread.change_running)
        self.targetID.connect(self.videoThread.chage_id)
        self.trackSignal.connect(self.videoThread.change_tracking)

        # 接受信号，连接槽函数
        # 来自camera
        self.videoThread.update_detected_frame.connect(self.updateDetectedFrame_slot)
        self.videoThread.update_detectedIDs.connect(self.updateDetectedIDs_slot)
        self.videoThread.camera_log.connect(self.printMessage)
        # 来自ui控件
        # 视觉
        self.detectButton.clicked.connect(self.detectOpenClose)
        self.lineEdit.returnPressed.connect(self.updateID)
        self.trackButton.clicked.connect(self.trackOpenClose)
        # 语音
        self.voice_enable_button.clicked.connect(self.voice_enable)
        self.voice_disable_button.clicked.connect(self.voice_disable)
        self.voicethread.update_signal.connect(self.update_text_browser)

        # 界面控制
        self.initUI()
        # 控制文本输出
        self.initTextBrowser()

        # ids
        self.ids = None

    def voice_enable(self):
        self.voicethread.start()

    def update_text_browser(self,keyword_idx):
        if keyword_idx == 1 and self.voicethread.isRunning() == 1:
            self.textBrowser.clear()
            self.textBrowser.append("请说话···")
            print(keyword_idx)
        elif keyword_idx == 0 and self.voicethread.isRunning() == 1:
            self.textBrowser.clear()
            self.textBrowser.append("正在录音···")
            print(keyword_idx)

    def voice_disable(self):
        self.voicethread.stop()
    def searchID(self, id):
        return torch.isin(id, self.ids)

    def updateID(self):
        """当按下返回建和回车建，先判断是否合法，再将其发给cameraThread"""
        id = self.lineEdit.text()
        if not id.isdigit():
            self.printMessage("输入格式错误，请重新输入")
        else:
            id = torch.tensor(int(id))
            if self.searchID(id):
                # 发送给cam
                self.targetID.emit(id)
                self.printMessage("已经跟踪目标id" + str(int(id)))
            else:
                self.printMessage(f"输入 ID{id} 不在当前id列表中,请重新输入")

    def receiveMessage(self, message):
        """
        如果要输出富文本，或添加输出逻辑，在该函数添加
        先接受数据，再处理数据，最后将数据打印
        这里是接受和处理数据槽函数
        """
        self.printMessage(message=message)

    def printMessage(self, message):
        """
        如果只发送文本，选用该函数
        """
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        message = timestamp + " " + message
        self.textBrowser.append(message)

    def initTextBrowser(self):
        """
        这里使用富文本，它只读，可表达html
        """
        # 设置设置自动换行和垂直和水平滚动
        self.textBrowser.setLineWrapMode(QTextEdit.WidgetWidth)
        self.textBrowser.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.textBrowser.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def print_status(self):
        print("eval(self.videoThread) status\t" + str(self.videoThread.isRunning()))

    def trackOpenClose(self):
        text = self.trackButton.text()
        if text == "打开跟踪功能":
            self.trackSignal.emit(True)
            self.receiveMessage("跟踪已开启")
            self.trackButton.setText("关闭跟踪功能")
        else:
            self.trackSignal.emit(False)
            self.receiveMessage("跟踪已关闭")
            self.trackButton.setText("打开跟踪功能")

    def detectOpenClose(self):
        if self.videoThread.isRunning():
            self.detectSignal.emit(False)
            self.detectButton.setText("开始检测")
            self.receiveMessage("已停止检测")
        else:
            self.videoThread.start()
            self.detectSignal.emit(True)
            self.detectButton.setText("停止检测")
            self.receiveMessage("已开始检测")

    def initUI(self):
        # self.setWindowTitle("Tiger")
        pass

    def updateDetectedFrame_slot(self, frame):
        qimg = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(qimg)
        self.detectedVideo.setPixmap(pixmap)

    def updateDetectedIDs_slot(self, new_ids):
        # 不在末尾放发送函数的原因是减少发送次数
        if new_ids is None:
            return
        if self.ids == None:
            self.ids = new_ids
        else:
            # 判断两个数组大小是否相同，只要有一点不同就用新的替换旧的
            old_length = len(self.ids)
            new_length = len(new_ids)
            if new_length != old_length:
                self.ids = new_ids
            else:
                for i in range(old_length):
                    if self.ids[i] != new_ids[i]:
                        self.ids = new_ids


class Integrate(QWidget):
    def __init__(self):
        super().__init__()

    def show_login(self):
        self.login = Login()
        self.login.switch_window.connect(self.show_main)
        self.login.ui.show()

    def show_main(self):
        ##登陆检查
        check_value=self.login_check()
        ##传参
        if check_value == 1:
            self.window = PlatForm()
            print()
            self.window.videoThread.source = "rtsp://" + self.login.admin_line.text()+":" + self.login.pw_line.text() + "@"+self.login.ip_line.text() + ":554/h264/ch1/main/av_stream"
            self.window.videoThread.cam_ctrl.DEV_IP = create_string_buffer(bytes(self.login.ip_line.text(),'utf8'))
            self.window.videoThread.cam_ctrl.DEV_USER_NAME = create_string_buffer(bytes(self.login.admin_line.text(),'utf8'))
            self.window.videoThread.cam_ctrl.DEV_PASSWORD = create_string_buffer(bytes(self.login.pw_line.text(),'utf8'))
            self.login.ui.close()
            self.window.ui.show()
        else :
            self.show_error_popup()

    def show_error_popup(self):
        error_popup = QMessageBox(self)
        error_popup.setIcon(QMessageBox.Warning)
        error_popup.setText('请重新输入IP、密码与用户名')
        error_popup.setWindowTitle('登录错误')
        error_popup.setStandardButtons(QMessageBox.Ok)
        error_popup.exec_()

    def login_check(self):
        test = Camera()
        test.DEV_USER_NAME = create_string_buffer(bytes(self.login.admin_line.text(),'utf8'))
        test.DEV_IP = create_string_buffer(bytes(self.login.ip_line.text(),'utf8'))
        test.DEV_PORT = 8000
        test.DEV_PASSWORD = create_string_buffer(bytes(self.login.pw_line.text(),'utf8'))
        (lUserId, device_info) = test.LoginDev()
        if lUserId < 0 :
            # 输入错误退出
            del test
            return 0
        else :
            del test
            return 1

if __name__ == "__main__":
    app = QApplication(sys.argv)
    plat = Integrate()
    plat.show_login()
    sys.exit(app.exec_())   