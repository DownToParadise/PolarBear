# 基于静态图片的行为识别，只需要安装yolov8、QT相关库
# 此版本识别与摄像头控制串行
# 一个通道为了取得处理后的视频，一个为了获取检测的id数目
import sys
sys.path.append("/home/yeung/code/mmaction2-main")
from qt2.yolo_queue import YoloQueue
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import cv2
import time
import numpy as np
import torch
import time
import torch
import cv2
import numpy as np
from ultralytics import YOLO
from camera_controlV1 import Camera

class videoProcessingThread(QThread):
    """设置摄像头显示页面"""
    update_frame = pyqtSignal(object)
    update_detected_frame = pyqtSignal(object)
    update_detection = pyqtSignal(object)
    camera_log = pyqtSignal(str)
    update_detectedIDs = pyqtSignal(object)
    # 传递摄像头控制信号
    update_PTZControl = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # 目标检测模型
        self.model = YOLO("yolov8n.pt")
        self.source = "rtsp://admin:DING123456@219.216.72.149:554/h264/ch1/main/av_stream"  # RTSP
        # self.source = 0
        # 设置目标跟踪
        self.Model = self.model.track(self.source, stream=True, classes=[0], persist=True)
        # 设置行为识别模型
        self.action_model = YOLO("/home/yeung/code/mmaction2-main/Models/yolov8/9_27_12/best.pt")
        self.action_label_map={'0': 'phone call', '1': 'take off jacket', '2': 'hand waving', '3': 'cheer up', 
                               '4': 'jump up', '5': 'play with phone', '6': 'sit down', 
                  '7': 'squat down', '8': 'stand', '9': 'taking a selfie', '10': 'walk'}
        self.num_frame = 10
        # 界面传来的控制信号
        self.running = False
        # 摄像头控制，其默认对摄像头参数进行配置及初始化
        self.cam_ctrl = Camera()
        # 摄像头函数调用成功
        self.lret = False
        # 摄像头跟踪，默认不启用
        self.tracking = False

        self.fps_window_size = 10
        self.target_id = torch.tensor(1)


    def ControlPTZ_V2(self, img, bbox, cam_ctrl):
        """重写逻辑
        1.0逻辑是设置一个图片中心点，一旦bbox的中心点与图片中心点就移动，避免过多移动导致的抖动
        2.0逻辑当两个点相差距离达到一定距离后再进行移动，减少移动次数
        3.0结合QT线程，再使用信号与槽机制传递参数，使摄像头的运动不干扰识别
        """
        img_height, img_width, _ = img.shape
        img_center_x = img_width / 2
        img_center_y = img_height / 2
        box_center_x = bbox[0][0].cpu().numpy()
        box_center_y = bbox[0][1].cpu().numpy()
        # 计算框中心与图像中心的差异
        diff_x = box_center_x - img_center_x
        diff_y = box_center_y - img_center_y

        # 根据位置差异选择控制命令
        # 设置移动的阈值，与中心相差多少时才启动云台运动
        threshold_x = 180  # 可以根据需要调整这个值
        threshold_y = 40
        speed_threshold = 0.4
        command = None
        speed = 7
        # 根据摄像头设置的运动速度和拍摄的场景幅度而定，最好只需发出一个指令就能使摄像头移动到位置上
        # 运动时间可以稍微长点，但是不能他多暂停
        field = 200
        if abs(diff_x) > threshold_x:
            print("diff_x",diff_x)
            dynamic_sleep = max(abs(diff_x) / field, 0.2)
            # 控制运动速度防止其猛冲
            if dynamic_sleep > speed_threshold:
                speed = 4
            if diff_x < -threshold_x:
                command = "PAN_LEFT"
            elif diff_x > threshold_x:
                command = "PAN_RIGHT"
            # 执行命令
            if command is not None:
                self.lret = cam_ctrl.NET_DVR_PTZControlWithSpeed_Other(command, dynamic_sleep, speed)
        
        if abs(diff_y) > threshold_y:
            print("diff_y", diff_y)
            dynamic_sleep = max(abs(diff_y) / field, 0.2)
            if dynamic_sleep > speed_threshold:
                speed = 4
            if diff_y < -threshold_y:
                command = "TILT_UP"
            elif diff_y > threshold_y:
                command = "TILT_DOWN"
            # 执行命令
            if command is not None:
                self.lret = cam_ctrl.NET_DVR_PTZControlWithSpeed_Other(command, dynamic_sleep, speed)

        if self.lret == 0 and (abs(diff_y) > threshold_y or abs(diff_x) > threshold_x):
            print("************cannot move cam********")
            self.camera_log.emit("camera cannot move cam, please check the code")

    def padding_bboximg(self, img, target_size=640):
        width, height, _ = img.shape
        # 缩放图片（保持宽高比）
        if max(width, height) > target_size:
            scaling_factor = target_size / max(width, height)
            new_width = int(width * scaling_factor)
            new_height = int(height * scaling_factor)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

            # 计算需要填充的边距
        delta_width = target_size - img.shape[1]
        delta_height = target_size - img.shape[0]
        top, bottom = delta_height // 2, delta_height - (delta_height // 2)
        left, right = delta_width // 2, delta_width - (delta_width // 2)

        # 填充图片，使其成为 640x640
        color = [0, 0, 0]  # 使用黑色进行填充
        padded_img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)

        return padded_img

    def crop_image(self, img, bboxes):
        """得到xyxy形式的bobox进行裁减并返回"""
        x1 = int(bboxes[0])
        y1 = int(bboxes[1])
        x2 = int(bboxes[2])
        y2 = int(bboxes[3])
        # y_max = max(y1, y2)
        # y_min = min(y1, y2)
        # x_max = max(x1, x2)
        # x_min = min(x1, x2)
        # bbox_img = img[y_min:y_max, x_min:x_max]
        bbox_img = img[y1:y2, x1:x2]
        return bbox_img
    
    def run(self):
        count = 0
        print_label = "recognizing..."
        action_label = ""
        action_label_acc = 0
        # max_size参数还需要调整
        action_queue = YoloQueue(max_size=30)

        # fps设置
        fps = 0
        fps_list = []
        prev_time = time.time()

        while True and self.running:

            # 推理，检测并跟踪
            # 这里是对每一帧都进行检测，也可以对连续的图片进行检测
            # 也可以考虑用yolo的关键点提取方法，因为只识别一个人所以比较简单
            results = next(self.Model)

            for i in range(len(results)):
                try:
                    self.update_detectedIDs.emit(results.boxes.id)
                    if results.boxes.id[i] != self.target_id:
                        continue
                except TypeError:
                    break
                result = results[i]
                img = result.orig_img
                # 数据处理
                print(img.shape)
                print(result.boxes.xyxy[0])
                bbox_img = self.crop_image(img, result.boxes.xyxy[0])
                padded_img = self.padding_bboximg(bbox_img)
                # 推理
                preds = self.action_model(padded_img, device=self.device, verbose=False)
                # 标签处理
                action_label = self.action_label_map[str(preds[0].probs.top1)]
                action_label_acc = preds[0].probs.top1conf.cpu().numpy()
                action_queue.enqueue(item=action_label)
               
                if count == self.num_frame:
                    print_label = action_queue.find_most_frequent()
                    count = 0
                else:
                    count += 1
                # 控制摄像头，默认关闭
                if self.tracking:
                    self.ControlPTZ_V2(img, result.boxes.xywh, self.cam_ctrl)

            # 计算帧率
            # 记录当前时间
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time)
            prev_time = curr_time
            # 添加到FPS列表并保持滑动窗口大小
            fps_list.append(fps)
            if len(fps_list) > self.fps_window_size:
                fps_list.pop(0)
            # 计算平均FPS
            avg_fps = sum(fps_list) / len(fps_list)

            # 绘图
            # 绘制框
            an_frame = results.plot()
            # 绘制帧率
            fps_label = f'FPS: {int(avg_fps)} + {print_label} + {(action_label_acc*100):.2f}%'
            cv2.putText(an_frame, fps_label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            # 显示界面
            self.update_detected_frame.emit(an_frame)
    
    # 接受界面传来的信号
    @pyqtSlot(bool)
    def change_running(self, running):
        self.running = running

    @pyqtSlot(bool)
    def change_tracking(self, tracking):
        self.tracking = tracking

    @pyqtSlot(object)
    def chage_id(self, id):
        if not torch.is_tensor(id):
            id = torch.tensor(id)
        self.target_id = id

