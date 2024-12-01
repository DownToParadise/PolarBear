# 基于cameraV2文件改进
# 使用实时编码推流
# 将控制代码去掉
import sys, os
# sys.path.append("D:\Code\mmaction2-main\qt2\\YOLOtracker")
path = os.getcwd()+"\\YOLOtracker"
sys.path.append(path)
from yolo_queue import YoloQueue
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
from hik import HKCam
from YOLOtracker.tracker import Tracker
import face_recognition 


class videoProcessingThread(QThread):
    """设置摄像头显示页面"""
    # 该frame用于发送可视化页面的图像
    update_detected_frame = pyqtSignal(object)
    update_detection = pyqtSignal(object)
    camera_log = pyqtSignal(str)
    update_detectedIDs = pyqtSignal(object)
    update_frame = pyqtSignal(object)
    # 此信号专门用来发送图像匹配未识别、目标丢失、目前无检测人物
    # 如果图像匹配未识别到目标人物，就跳到随机匹配功能
    # 随机匹配如果未识别到人物，就切换到下一个人物，目前切换到下一个人物
    # 0为未检测到人型号，1为目标丢失信号，2为图像匹配失败信号，3用于重置目标丢失信号
    target_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # 设置摄像头参数
        self.Cam = None
        self.cam_ip = None
        self.cam_name = None
        self.cam_pass = None

        # 目标检测模型，以及配置目标跟踪
        self.tracker = Tracker()
        self.tracker.init_tracker()
        print(os.getcwd())
        self.action_model = YOLO("weights\\10_15\\best.pt", verbose=False)
        # self.action_label_map={'0': 'phone call', '1': 'take off jacket', '2': 'hand waving', '3': 'cheer up', 
        #                        '4': 'jump up', '5': 'play with phone', '6': 'sit down', 
        #           '7': 'squat down', '8': 'stand', '9': 'taking a selfie', '10': 'walk'}
        # 设置行为识别读取参数
        self.num_frame = 10 
        self.action_label_map = {'0': 'cheer_up', '1': 'hand_waving', '2':'jump_up', '3': 'phone_call', '4': 'pick_up','5':'play_with _phone', 
                                 '6':'sit_down', '7': 'squat_down', '8':'stand', '9':'taking_a_selfie', '10':'walk'}
        
        self.running = False
        # 摄像头控制，其默认对摄像头参数进行配置及初始化
        # self.cam_ctrl = Camera()
        # 摄像头函数调用成功
        self.lret = False
        self.cam_ctrl_finshed = True
        # 摄像头跟踪，默认不启用，该版本默认开启，跟踪已
        self.tracking = True

        # 记录摄像头云台移动次数
        self.ctrl_count = 0
        self.fps_window_size = 10
        self.target_id = torch.tensor(0)  # 默认为1
        self.acc_thre = 0.3

        # 识别结果
        self.diff_x = 0
        self.diff_y = 0

        # 图像大小
        self.frame_width = 0
        self.frame_height = 0

        self.imageFile = None
        self.goal_image = None
        self.goal_face_encoding = None
        self.known_face_encodings = None
        self.known_face_names = None
        # 多少帧未检测到人脸就报错，自动切换随机模式
        self.imageMatch_tolerance_thread = 50
        self.imageMatch_success = False

        self.target_lost_count = 0
        
    def CamInit(self, ip, name, passwd):
        # 初始化摄像头
        self.cam_ip = ip
        self.cam_name = name
        self.cam_pass = passwd
        self.Cam = HKCam(self.cam_ip, self.cam_name, self.cam_pass)
        _, frame = self.Cam.read()
        self.frame_height, self.frame_width, _ = frame.shape
        return self.Cam.init_info
        
    def ControlPTZ_V2_(self, label, bbox):
        """重写逻辑
        1.0逻辑是设置一个图片中心点，一旦bbox的中心点与图片中心点就移动，避免过多移动导致的抖动
        2.0逻辑当两个点相差距离达到一定距离后再进行移动，减少移动次数
        3.0结合QT线程，再使用信号与槽机制传递参数，使摄像头的运动不干扰识别

        改为偏移量计算
        """
        img_center_x = self.frame_width / 2
        img_center_y = self.frame_height / 2
        box_center_x = int(bbox[0] + bbox[2] / 2)
        box_center_y = int(bbox[1] + bbox[3] / 2)
        # 计算框中心与图像中心的差异
        diff_x = int(box_center_x - img_center_x)
        diff_y = int(box_center_y - img_center_y)

        data = label, diff_x, diff_y
        self.update_detection.emit(data)

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
        bbox_img = img[y1:y2, x1:x2]
        return bbox_img
    
    def tlwh_to_xyxy(self, bbox, img_size=640):
        "左上角加wh变为左上角加右下角，并返回xcenter和ycenter"
        bbox[0] = int(bbox[0] * self.frame_width / img_size)
        bbox[1] = int(bbox[1] * self.frame_height / img_size)
        bbox[2] = int(bbox[2] * self.frame_width / img_size)
        bbox[3] = int(bbox[3] * self.frame_height / img_size)
        bbox[2]=int(bbox[0] + bbox[2])
        bbox[3]=int(bbox[1] + bbox[3])
        return bbox

    def match_face(self, frame, results):
        T_id = False
        # 加载图片
        if self.known_face_encodings is None:
            return T_id
        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            
            if True in matches:  # 如果有匹配成功
                # 找到第一个匹配的位置
                first_match_index = matches.index(True)
                name = self.known_face_names[first_match_index]

                # 为人脸画边界框
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                center_x = int((left + right) / 2)
                center_y = int((top + bottom) / 2)
                # 在人脸边界框下方绘制该人脸所属人的名字
                cv2.rectangle(frame, (left, bottom - 20), (right, bottom), (0, 0, 255), cv2.FILLED)
                cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.circle(frame, (center_x, center_y), 2, (0, 255, 0), -1)
                # 找到离face 最近的bbox然后进行匹配
                for id, bbox in results.items():
                    # print("id\t", id, "bbox\t", bbox, "face\t", center_x, center_y)
                    # print("face_recong bbox", bbox)
                    # 匹配结果比较简单
                    if bbox[0] <= center_x <= bbox[2] and bbox[1] <= center_y <= bbox[3]:
                        # print("face_recong id \t",id)
                        self.camera_log.emit("图像匹配成功ID"+str(id))
                        self.imageMatch_success = True
                        self.target_id = id
                        T_id = True 
        return  T_id

    def run(self):
        action_count = 0
        print_label = "recognizing..."
        print_acc = 0
        action_label = ""
        action_label_acc = 0
        fps_label = None
        # max_size参数还需要调整
        action_queue = YoloQueue(max_size=30)
        self.camera_log.emit("默认匹配目标ID"+str(int(self.target_id)))
        image_tolerance = 0

        # fps设置
        fps = 0
        fps_list = []
        prev_time = time.time()
        # count = 1
        
        if self.Cam is None:
            print("Error! Cam is not Init!")
        
        # 改正这里self.cam持续输出图片
        while True and self.running:
            _, frame = self.Cam.read()
            img = frame.copy()
            # 推理，检测并跟踪
            # 这里是对每一帧都进行检测，也可以对连续的图片进行检测
            # 也可以考虑用yolo的关键点提取方法，因为只识别一个人所以比较简单
            detect_num, results, ids= self.tracker.yolov8_tracker(frame)

            # 每次识别完后都发送id列表
            self.update_detectedIDs.emit(ids)
            # self.camera_log.emit(str(detect_num))
            if detect_num == 0:
                self.target_signal.emit(0)
                # 如果未识别到就发送空白帧,并跳出循环
                self.update_detected_frame.emit(frame)
                self.update_frame.emit(img)
                continue
            
            # 人脸识别确定目标
            if self.imageMatch_success == False:
                if self.imageFile != None:
                    # print(self.imageFile)
                    # 匹配时不开启行为识别
                    image_match_flag = self.match_face(frame, results) 
                    # print("image match", image_match_flag)
                    # 匹配时间说明
                    # 这个可以放在mainplatform中
                    if image_match_flag == False:
                        # print("2")
                        self.target_signal.emit(2)
                        continue
                    
            # 找到对应的目标
            i = 0
            for id, bbox in results.items():
                # 只有目标丢失后才会触发目标寻找
                try:
                    if id == self.target_id:
                        # color = (B, G, R)
                        color = (0, 0, 255)
                        thickness = 2
                        cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])),
                            (int(bbox[2]), int(bbox[3])),
                            color=color, thickness=thickness)
                        cv2.putText(frame, f'ID: {id}', (int(bbox[0]), int(bbox[1] - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color=color, thickness=thickness)
                        # 在外置页面上进行展示
                        color = (0, 0, 255)
                        thickness = 2
                        cv2.rectangle(img, (int(bbox[0]), int(bbox[1])),
                            (int(bbox[2]), int(bbox[3])),
                            color=color, thickness=thickness)
                        # cv2.putText(frame, f'ID: {id}', (int(bbox[0]), int(bbox[1] - 10)),
                        #     cv2.FONT_HERSHEY_SIMPLEX, 0.8, color=color, thickness=thickness)
                    else:
                        # 没找到flag +1，并跳出循环进行后续操作
                        i += 1
                        color = (200, 0, 0)
                        thickness = 2
                        cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])),
                            (int(bbox[2]), int(bbox[3])),
                            color=color, thickness=thickness)
                        cv2.putText(frame, f'ID: {id}', (int(bbox[0]), int(bbox[1] - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color=color, thickness=thickness)
                        continue
                except TypeError:
                    break
                # 是否开启图像匹配
                # 数据处理
                # xyxy = self.tlwh_to_xyxy(result.tlwh)
                # 找到了目标队形
                self.target_signal.emit(3)
                xyxy = bbox
                bbox_img = self.crop_image(frame, xyxy)
                padded_img = self.padding_bboximg(bbox_img)
                # 推理
                preds = self.action_model(padded_img, device=self.device, verbose=False)
                # 标签处理
                action_label = self.action_label_map[str(preds[0].probs.top1)]
                action_label_acc = preds[0].probs.top1conf.cpu().numpy()
                if action_label_acc <= self.acc_thre:
                    continue
                action_preds = [action_label, action_label_acc]
                action_queue.enqueue(item=action_preds)

                # 将显示的识别数据和发送的数据分开，可在页面单独显示该画面
                if action_count == self.num_frame:
                    print_label, print_acc = action_queue.find_most_frequent()
                    action_count = 0
                else:
                    action_count += 1
                # 控制摄像头
                if self.tracking and self.cam_ctrl_finshed:
                    # 该版本将摄像头控制功能取消，改为偏移量计算，需要将识别结果与跟踪同步传递
                    # 默认开启
                    self.ControlPTZ_V2_(print_label, xyxy)
                
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
            # 因为上面都是浅拷贝，所以在tracker中的画图在此处有效
            # 绘制帧率
            if i == detect_num:
                self.target_signal.emit(1)
            else:
                # ID识别到了才画，更上面指令一样识别到了，只不过这里要做的是每过多少帧处理一次，上面是每帧都处理
                try:
                    # 这个地方要改一下id变了还在识别
                    if action_label_acc >= self.acc_thre:
                        fps_label = f'ID{int(self.target_id)} FPS: {int(avg_fps)} + {print_label} + {(print_acc*100):.2f}%'
                except TypeError:
                    fps_label = ""
                # 如果绿色标签没有显示，就是acc_thre给的太高
                cv2.putText(frame, fps_label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # 无论图像是何种都需要将其发送出去，以保证页面的流畅性
            self.update_detected_frame.emit(frame)
            self.update_frame.emit(img)
            
    # 接受界面传来的信号
    @pyqtSlot(bool)
    def change_running(self, running):
        self.running = running

    @pyqtSlot(bool)
    def change_tracking(self, tracking):
        self.tracking = tracking

    @pyqtSlot(object)
    def chage_id(self, id):
        print(f"Sig Chaged ID tracking is {self.tracking}\tcam ctrl is {self.cam_ctrl_finshed}")
        if not torch.is_tensor(id):
            id = torch.tensor(id)
        self.target_id = id
        
    @pyqtSlot(bool)
    def change_cam_ctrl_finshed(self, sig):
        print(f"Sig Finshed ID tracking is {self.tracking}\tcam ctrl is {self.cam_ctrl_finshed}")
        self.cam_ctrl_finshed = sig

    def chage_imagefile(self, path):
        self.imageFile = path
        # print(str(path))
        if self.imageFile != None:
            # print(self.imageFile)   
            try:
                self.goal_image = face_recognition.load_image_file(self.imageFile)
                self.goal_face_encoding = face_recognition.face_encodings(self.goal_image)[0]
            except AttributeError:
                pass
            self.known_face_encodings = [
                    self.goal_face_encoding,
                ]
            self.known_face_names = [
                "goal",
            ]
            # 将标志位置为False以开启人脸识别功能
            self.imageMatch_success = False
        else:
            self.imageMatch_success = True
            pass

if __name__ == "__main__":
    video = videoProcessingThread()
    camIP ='219.216.72.123'
    DEV_PORT = 8000
    username = 'admin'
    password = 'ding123456'
    # HIK = HKCam(camIP, username, password)
    video.CamInit(camIP, username, password)
    _, frame = video.Cam.read()
    cv2.imshow("test", frame)
    while True:
        _, frame = video.Cam.read()
        cv2.imshow("test", frame)
        if cv2.waitKey(1) & 0xff == ord("q"):
            break