# 只有识别功能，不带摄像头跟踪功能
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys, os
from PyQt5 import uic
import torch
from cameraV3 import videoProcessingThread
from voice_thread import voice_thread
import time
from ctypes import create_string_buffer
from camera_controlV1 import Camera
import threading
from camera import videoProcessingThread2
import cv2
import numpy as np
from FontSet import FontSettingsDialog

# 登录界面
class Login(QWidget):
    switch_window = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("configs/ui_files/login.ui")
        #登录界面ui控件
        self.ip_line = self.ui.ip_line
        self.admin_line = self.ui.admin_line
        self.pw_line = self.ui.pw_line
        self.login_button = self.ui.login_button
        #连接槽
        self.login_button.clicked.connect(self.switchwindow)

    def switchwindow(self):
        self.switch_window.emit()

class PlatForm(QMainWindow):
    # 线程生命区
    videoThread = videoProcessingThread()
    videoThread2 = videoProcessingThread2()
    #语音线程
    voiceThread=voice_thread()
    # 信号
    detectSignal = pyqtSignal(bool)
    trackSignal = pyqtSignal(bool)
    targetID = pyqtSignal(object)
    # 发送图片
    imageFile = pyqtSignal(object)
    # 单独图片发送信号
    camera_signal = pyqtSignal(bool)

    def __init__(self):
        super(PlatForm, self).__init__()
        # 这么写的原因时因为海康的API中更改了工作目录
        # print(os.getcwd())
        self.ui = uic.loadUi("configs/ui_files/platform.ui")
        self.visiualUI = uic.loadUi("configs/ui_files/page.ui")

        # 获取ui设置
        self.detectedVideo = self.ui.video
        self.detectButton = self.ui.detectButton
        self.textBrowser = self.ui.textBrowser
        self.lineEdit = self.ui.lineEdit
        self.fontSettingButton = self.ui.fontSettingButton
        self.setttingButton()
        # self.trackButton = self.ui.trackButton
        self.visiualButton = self.ui.visiualButton
        self.randomMatchButton = self.ui.trackButton_2
        self.faceMatchButton = self.ui.trackButton_3
        # self.prioriFaceMatchButton = self.ui.trackButton_4
        # 语音控件
        self.voice_enable_button = self.ui.voice_enable
        self.voice_disable_button = self.ui.voice_disable
        # 摄像头控制按钮
        self.CamUPButton = self.ui.CamUp
        self.CamDownButton = self.ui.CamDown
        self.CamLeftButton = self.ui.CamLeft
        self.CamRightButton = self.ui.CamRight
        # 外置可视化页面
        self.detectedVideo2 = self.visiualUI.video
        self.ImagLabel = self.ui.ImagLabel
        
        # 发送信号
        self.detectSignal.connect(self.videoThread.change_running)
        self.trackSignal.connect(self.videoThread.change_tracking)
        self.targetID.connect(self.videoThread.chage_id)
        self.randomMatchButton.clicked.connect(self.randomID)              #随机id
        self.targetFlag = 0                                     # 随机目标跟踪符号，0为默认模式，1为随机ID模式，2为输入指定图片模式，3为默认图片模式
        self.randomFlag = False                                 # 随机匹配FLAG
        self.imageFlag = False                                  # 随机输入图像进行匹配  
        self.imageFile.connect(self.videoThread.chage_imagefile)
        self.camera_signal.connect(self.videoThread2.ChangeRunning)

        # 输出栏字体设置
        self.fontSettingButton.clicked.connect(self.open_font_setting_dialog)

        # 接受来自camera信号
        # 传画面
        self.videoThread.update_detected_frame.connect(self.updateDetectedFrame_slot)
        self.videoThread.update_frame.connect(self.updateDetectedFrame_slot2)
        # 传识别到的ID信号，这两个信号可以放到一起
        self.videoThread.update_detectedIDs.connect(self.updateDetectedIDs_slot)
        self.videoThread.target_signal.connect(self.signal_process)

        # 重置ID
        # 识别结果
        self.videoThread.update_detection.connect(self.updateDetected)
        self.videoThread.camera_log.connect(self.printMessage)
        
        # 来自ui控件
        # 视觉
        self.detectButton.clicked.connect(self.detectOpenClose)
        self.lineEdit.returnPressed.connect(self.updateID)
        # self.trackButton.clicked.connect(self.trackOpenClose)
        self.visiualButton.clicked.connect(self.visiualPageOpen)
        self.faceMatchButton.clicked.connect(self.imageMatch)
        # 语音
        self.voice_enable_button.clicked.connect(self.voice_enable)
        self.voice_disable_button.clicked.connect(self.voice_disable)
        self.voiceThread.update_signal.connect(self.update_text_browser)
        self.voiceThread.voiceText_BeiBei.connect(self.voice_beibei)
        self.voiceThread.voiceText_User.connect(self.voice_user)
        # 摄像头云台控制
        self.CamUPButton.clicked.connect(self.cam_ctrl_up)
        self.CamDownButton.clicked.connect(self.cam_ctrl_down)
        self.CamLeftButton.clicked.connect(self.cam_ctrl_left)
        self.CamRightButton.clicked.connect(self.cam_ctrl_right)
        self.speed = 5
        self.sleeptime = 1

        # 界面控制
        self.initUI()
        # 控制文本输出
        self.initTextBrowser()

        # ids
        self.ids = None
        self.id = 0
        self.CamCtrl = None
        self.detectFalseCount = 0   # 未检测到的次数
        self.detectFalseCount_thre = 30

        # 图像为匹配次数
        self.image_match_tolerance = 0
        self.image_match_thre = 10

        # 目标未识别到
        self.person_lost_tolerance = 0
        self.person_lost_thre = 20
        self.person_confirm = 0
        self.person_confirm_thre = 10

    def open_font_setting_dialog(self):
        # pass
        font = self.textBrowser.font()
        dialog = FontSettingsDialog(self, font)
        if dialog.exec_() == QDialog.Accepted:
            selected_font = dialog.get_selected_font()
            self.textBrowser.setFont(selected_font)

    def setttingButton(self):
        print("settingButton", os.getcwd())
        pixmap = QPixmap("configs\pics\\fontsetting.png")
        self.fontSettingButton.setIcon(QIcon(pixmap))

    def signal_process(self, signal):
        if signal == 0:
            # 该帧未检测到人，已在id类别更新处处理
            self.detectFalseCount += 1
            if self.detectFalseCount % self.detectFalseCount_thre == 0:
                self.showMessage("当前未检测到人体...."+str(self.detectFalseCount // self.detectFalseCount_thre))
                if self.detectFalseCount == self.detectFalseCount_thre*10:
                    self.showMessage("<b>多次未检测到人体，请排查场景中是否有人体</b>")
                    self.detectFalseCount = 0

        elif signal == 1:
            # 只在不是0的前提下，才肯能会发送1
            # 这里应该还要加一个回复设置，如果匹配到了目标就将其tolerance置回0
            # print("singal1", signal)
            # 目标丢失,如果目标丢失,就随机在当前目标中选中一个目标
            self.person_lost_tolerance += 1
            if self.person_lost_tolerance % self.person_lost_thre == 0:
                self.showMessage("未检测到目标人物...."+str(self.person_lost_tolerance//self.person_lost_thre))
                if self.person_lost_tolerance == self.person_lost_thre*5:
                    # 判断当前打开的是什么功能，关闭这些功能，并随机匹配
                    if self.randomFlag:
                        # 关闭其功能就是在模拟点击动作
                        self.randomMatchButton.click()
                        # self.randomFlag = False
                        # self.showMessage("已关闭随机匹配模式")
                    if self.imageFlag:
                        self.faceMatchButton.clikc()
                    
                    self.person_lost_tolerance = 0
                    # 重新筛选信息
                    self.id = self.ids[0]
                    self.targetID.emit(self.id)
                    self.showMessage("<b>目标已丢失，随机匹配目标ID"+str(int(self.id))+"</b>")

        elif signal == 2:
            # print("signal2: ", signal)
            self.image_match_tolerance += 1
            if self.image_match_tolerance % self.image_match_thre == 0:
                self.showMessage("图像匹配中...."+str(self.image_match_tolerance//self.image_match_thre))
                if self.image_match_tolerance == self.image_match_thre*5:
                    # 将设备信息重置
                    self.imageFile.emit(None)
                    self.faceMatchButton.click()
                    self.image_match_tolerance = 0
                    # 清空显示图像
                    self.ImagLabel.setText("Image None")
                    
                    # 重新筛选信息
                    self.id = self.ids[0]
                    self.targetID.emit(self.id)
                    self.showMessage("<b>图像匹配失败，随机匹配目标ID"+str(int(self.id))+"</b>")
        
        elif signal==3:
            # signal发出信号,重置tolerance信号
            # print("signal3", signal)
            self.person_confirm += 1
            if self.person_confirm == self.person_confirm_thre :
                self.person_confirm = 0
                self.person_lost_tolerance = 0
                    

    def pic_find(self):
        """找pics文件夹中是否存有图片，如果没有图片则返回None，如果有多个图片则随意取一个图片"""
        pwd = os.getcwd()
        path = pwd + "\\faces"
        if os.path.exists(path) and os.path.isdir(path):
            pass
        else:
            self.showMessage("默认人脸识别文件夹不存在，请保证项目文件夹中有faces文件夹存在，且存放一张目标人脸照片")
        filename = None
        # 定义图片文件的扩展名
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp']
        
        # 遍历当前目录中的文件
        for filename in os.listdir(path):
            # 检查文件扩展名是否在图片扩展名列表中
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                # 返回找到的图片文件的完整路径
                return os.path.join(path, filename)
        
        # 如果没有找到图片文件，则返回 None
        return None

    def showImage(self, label, pixmap):
        # 在某个label中显示image
        if pixmap.isNull():
            label.setText("Failed to load image.")
            self.showMessage("Failed to load image.")
        else:
            label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def imageMatch(self):
        text = self.faceMatchButton.text()
        filename = None
        if text == "打开图像匹配模式":
            if self.randomFlag:
                self.showMessage("<b>请先关闭随机匹配模式</b>")
                return
            self.showMessage("图像匹配模式已打开")
            self.imageFlag = True
            self.showMessage("读取默认图像")
            filename = self.pic_find()
            if filename == None:
                self.showMessage("不存在默认图像")
                filename = self.imageOpen()
            # 发送图片进入camera中进行匹配，打开图像匹配，读取图像，识别图像，从frame中读取相似的图像，
            # 并进行匹配，然后与每个bbox计算距离，距离最近的为target ID
            self.faceMatchButton.setText("关闭图像匹配模式")
            if filename == None:
                self.showMessage("图像读取失败，关闭图像匹配模式...")
                self.faceMatchButton.click()
            else:
                self.showMessage("读取图片：" + filename)
                pixmap = QPixmap(filename)
                self.showImage(self.ImagLabel, pixmap)
        else:
            filename = None
            self.ImagLabel.setText("Image None")
            self.showMessage("图像匹配模式已关闭")
            self.imageFlag = False
            self.faceMatchButton.setText("打开图像匹配模式")
        self.imageFile.emit(filename)
        return filename

    def imageOpen(self, ):
        options = QFileDialog.Options()
        filename = None
        # 如果点击取消返回空字符串
        filename, _ = QFileDialog.getOpenFileName(self, "Select Image File", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.gif);;All Files (*)", options=options)
        if filename == "":
            filename = None
        return filename

    def randomID(self):
        text = self.randomMatchButton.text()
        if self.ids is None:
            self.showMessage("ID 目前为空，请重新尝试！！")
            return
        if text == "打开随机匹配模式":
            if self.imageFlag:
                self.showMessage("<b>请先关闭图像匹配模式</b>")
                return
            self.showMessage("随机匹配模式已打开")
            self.randomFlag = True
            self.randomID_()
            self.randomMatchButton.setText("关闭随机匹配模式")
        else:
            self.showMessage("随机匹配模式已关闭")
            self.randomFlag = False
            self.randomMatchButton.setText("打开随机匹配模式")
    
    def randomID_(self):
        # 随机更改id
        # ids为空的情况已经考虑
        # 考虑目标丢失的鲁棒性
        # 考虑目标丢失的情况
        if self.randomFlag:
            random_index = torch.randint(0, len(self.ids), (1,)).item()
            self.id = self.ids[random_index]
            self.targetID.emit(self.id)
            self.printMessage("已经匹配目标ID" + str(int(self.id)))
            return self.id
        else:
            pass
        
    def updateDetected(self, data):
        # 此处留给plc传递信号逻辑
        data = str(data)
        # self.showMessage(data)

    def updateDetectedFrame_slot2(self, frame):
        # 将画面传递给外置可视化页面
        # 还是使用一个画面
        if self.visiualUI.isHidden():
            text = self.visiualButton.text()
            if text != "打开可视化页面":
                self.visiualButton.setText("打开可视化页面")
        else:
            # 只需要要将label resize windown一样大，图片使用setPixmap会自适应使用
            width = self.visiualUI.width()
            height = self.visiualUI.height()
            self.detectedVideo2.resize(width, height)
            qimg = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_BGR888)
            pixmap = QPixmap.fromImage(qimg)
            self.detectedVideo2.setScaledContents(True)
            self.detectedVideo2.setPixmap(pixmap)
            
    def visiualPageOpen(self):
        text = self.visiualButton.text()
        if text == "打开可视化页面":
            # self.videoThread2.start()
            self.visiualUI.show()
            self.showMessage("可视化页面已打开")
            self.visiualButton.setText("关闭可视化页面")
        else:
            # self.videoThread2.stop()
            self.visiualUI.close()
            self.showMessage("可视化页面已关闭")
            self.visiualButton.setText("打开可视化页面")

    def voice_beibei(self, mes):
        mes = "北北:" + mes
        self.showMessage(mes)
        
    def voice_user(self, mes):
        mes = "你:  " + mes
        self.showMessage(mes)

    def CamInit(self, ip, name, password):
        self.CamCtrl = Camera(ip, name, password)

    def cam_ctrl_up(self):
        command = "TILT_UP"
        process = threading.Thread(target=self.CamCtrl.NET_DVR_PTZControlWithSpeed_Other, args=(command, self.sleeptime, self.speed))
        process.start()

    def cam_ctrl_down(self):
        command = "TILT_DOWN"
        process = threading.Thread(target=self.CamCtrl.NET_DVR_PTZControlWithSpeed_Other, args=(command, self.sleeptime, self.speed))
        process.start()

    def cam_ctrl_left(self):
        command = "PAN_LEFT"
        process = threading.Thread(target=self.CamCtrl.NET_DVR_PTZControlWithSpeed_Other, args=(command, self.sleeptime, self.speed))
        process.start()

    def cam_ctrl_right(self):
        command = "PAN_RIGHT"
        process = threading.Thread(target=self.CamCtrl.NET_DVR_PTZControlWithSpeed_Other, args=(command, self.sleeptime, self.speed))
        process.start()

    def voice_enable(self):
        self.voiceThread.start()

    def update_text_browser(self, keyword_idx):
        if keyword_idx == 1 and self.voiceThread.isRunning() == 1:
            # self.textBrowser.clear()
            self.printMessage("请说话···")
            print(keyword_idx)
        elif keyword_idx == 0 and self.voiceThread.isRunning() == 1:
            # self.textBrowser.clear()
            self.printMessage("正在录音···")
            print(keyword_idx)

    def voice_disable(self):
        self.voiceThread.stop()
        self.printMessage("语音已停止")

    def searchID(self, id):
        temp = torch.isin(id, self.ids)
        # if not temp:
        #     self.showMessage("目标丢失")
        return temp

    def updateID(self):
        """指定目标ID输入功能，当按下返回建和回车建，先判断是否合法，再将其发给cameraThread"""
        id = self.lineEdit.text()
        if not id.isdigit():
            self.printMessage("输入格式错误，请重新输入")
        else:
            self.id = torch.tensor(int(id))
            if self.searchID(self.id):
                # 发送给cam
                self.targetID.emit(self.id)
                self.printMessage("已经匹配目标ID" + str(int(self.id)))
            else:
                self.printMessage(f"输入 ID{self.id} 不在当前id列表中,请重新输入")

    def showMessage(self, message):
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
            # self.showMessage("跟踪已打开")
            # self.trackButton.setText("关闭跟踪功能")
        else:
            self.trackSignal.emit(True)
            # self.showMessage("跟踪已关闭")
            # self.trackButton.setText("打开跟踪功能")
        self.printMessage("该版本已取消跟踪功能")

    def detectOpenClose(self):
        if self.videoThread.isRunning():
            self.detectSignal.emit(False)
            self.detectButton.setText("开始检测")
            self.showMessage("已停止检测")
        else:
            #print(self.videoThread.source)
            self.videoThread.start()
            self.detectSignal.emit(True)
            self.detectButton.setText("停止检测")
            self.showMessage("已开始检测")

    def initUI(self):
        # self.setWindowTitle("Tiger")
        pass

    def updateDetectedFrame_slot(self, frame):
        qimg = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(qimg)
        self.detectedVideo.setPixmap(pixmap)
        # self.detectedVideo.setScaledContents(True)

    def updateDetectedIDs_slot(self, new_ids):
        # print("this is updateDetectedIDS\t", new_ids)
        # 不在末尾放发送函数的原因是减少发送次数
        # 看一下，如果变化过于频繁就直接选择赋值
        # if len(new_ids) == 0:
        #     self.detectFalseCount += 1
        #     if self.detectFalseCount % 20 == 0:
        #         self.showMessage("当前未检测到人体...."+str(self.detectFalseCount // 20))
        #         if self.detectFalseCount == 200:
        #             self.detectFalseCount = 0
        #     return
        if self.ids is None:
            self.ids = new_ids
        else:
            # 根据数组长度判断大小是否两个数组是否一致
            old_length = len(self.ids)
            new_length = len(new_ids)
            if new_length != old_length:
                # 不一样就直接赋值
                # print("from \t", self.ids)
                self.ids = new_ids
                # print("to ids\t", self.ids)
            else:
                # 一样就进行比对   
                for i in range(old_length):
                    if self.ids[i] != new_ids[i]:
                        # print("from \t", self.ids)
                        self.ids = new_ids

class Integrate(QWidget):
    def __init__(self):
        super().__init__()
        self.name = ""
        self.ip = ""
        self.password = ""
        self.init_info = 0
        self.window = PlatForm()
        
    def show_login(self):
        self.login = Login()
        # 第一个执行的函数
        self.login.switch_window.connect(self.show_main)
        self.login.ui.show()

    def show_main(self):
        ##登陆检查
        check_value=self.login_check()
        ##传参
        if check_value == 1:
            self.login.ui.close()
            self.window.ui.show()
        else :
            print("self", self.init_info)
            if self.init_info == 1:
                self.show_error_popup()
            elif self.init_info == 3:
                self.camera_cannot_find()
            elif self.init_info == 7:
                self.camera_ip_error()

    def camera_ip_error(self):
        error_popup = QMessageBox(self)
        error_popup.setIcon(QMessageBox.Warning)
        error_popup.setText('请重新输入摄像头IP')
        error_popup.setWindowTitle('登录错误')
        error_popup.setStandardButtons(QMessageBox.Ok)
        error_popup.exec_()

    def show_error_popup(self):
        error_popup = QMessageBox(self)
        error_popup.setIcon(QMessageBox.Warning)
        error_popup.setText('请重新输入密码或用户名')
        error_popup.setWindowTitle('登录错误')
        error_popup.setStandardButtons(QMessageBox.Ok)
        error_popup.exec_()

    def camera_cannot_find(self):
        error_popup = QMessageBox(self)
        error_popup.setIcon(QMessageBox.Warning)
        error_popup.setText('未找到摄像头！请检查摄像头是否打开或检查本地网络设置')
        error_popup.setWindowTitle('登录错误')
        error_popup.setStandardButtons(QMessageBox.Ok)
        error_popup.exec_()

    def login_check(self):
        test = Camera()
        self.name = self.login.admin_line.text()
        self.ip = self.login.ip_line.text()
        self.password = self.login.pw_line.text()
        test.DEV_IP = create_string_buffer(bytes(self.ip, "utf8"))
        test.DEV_USER_NAME = create_string_buffer(bytes(self.name, "utf8"))
        test.DEV_PASSWORD = create_string_buffer(bytes(self.password, "utf8"))
        test.DEV_PORT = 8000
        (lUserId, device_info) = test.LoginDev()
        print("tesst", lUserId)
        if lUserId < 0 :
            # 输入错误退出
            self.init_info = test.Objdll.NET_DVR_GetLastError()
            # print(self.init_info)
            del test
            return 0
        else :  
            self.window.CamInit(self.ip, self.name, self.password)
            self.window.videoThread.CamInit(self.ip, self.name, self.password)
            self.window.videoThread2.CamInit(self.ip, self.name, self.password)
            del test
            return 1
        

if __name__ == "__main__":
    app = QApplication(sys.argv) 
    plat = Integrate()
    plat.show_login()
    sys.exit(app.exec_())   