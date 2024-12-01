import sys
from ultralytics import YOLO
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QLineEdit
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import numpy as np
from hik import HKCam

"""
只用于产生独立与图像处理的视频流程
"""
class videoProcessingThread2(QThread):
    # 用于发送可视化页面
    update_frame = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.Cam = None
        self.cam_ip = None
        self.cam_name = None
        self.cam_pass = None
        self.running = False

    def CamInit(self, ip, name, passwd):
        # 初始化摄像头
        self.cam_ip = ip
        self.cam_name = name
        self.cam_pass = passwd
        self.Cam = HKCam(self.cam_ip, self.cam_name, self.cam_pass)
        _, frame = self.Cam.read()
        self.frame_height, self.frame_width, _ = frame.shape
        return self.Cam.init_info
    
    def run(self):
        if self.Cam is None:
            print("传递参数的摄像头未初始化")
        while True and self.running:
            _, frame = self.Cam.read()
            self.update_frame.emit(frame)

    @pyqtSlot(bool)
    def ChangeRunning(self, flag):
        self.running = flag