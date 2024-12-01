import sys, os

import numpy as np
import torch
import cv2

# trackers
from trackers.byte_tracker import ByteTracker
from trackers.sort_tracker import SortTracker
from trackers.botsort_tracker import BotTracker
from trackers.c_biou_tracker import C_BIoUTracker
from trackers.ocsort_tracker import OCSortTracker
from trackers.deepsort_tracker import DeepSortTracker

# YOLOv8 modules
try:
    from ultralytics import YOLO
    from yolov8_utils.postprocess import postprocess as postprocess_yolov8

except Exception as e:
    print('Load yolov8 fail. If you want to use yolov8, please check the installation.')
    pass

TRACKER_DICT = {
    'sort': SortTracker,
    'bytetrack': ByteTracker,
    'botsort': BotTracker,
    'c_bioutrack': C_BIoUTracker,
    'ocsort': OCSortTracker,
    'deepsort': DeepSortTracker
}

class Tracker():

    def __init__(self):
        self.obj='../jin.mp4' #or camera

        self.detector = 'yolov8' #被我改没用了
        self.tracker = 'ocsort'
        self.reid_model = 'deepsort'
        self.kalman_format = 'ocsort'
        self.img_size = 640
        self.device = '0'

        self.conf_thresh = 0.5
        self.nms_thresh = 0.3
        self.iou_thresh = 0.3


        self.detector_model_path= './weights/yolov8s.pt'
        #ocsort没用过这两个 不过别的会用到
        self.reid_model_path = './weights/ckpt.t700'
        self.dhn_path = './weights/DHN.pth'

        self.discard_reid = False #discard reid model, only work in bot-sort etc. which need a reid part
        self.track_buffer = 100
        self.gamma =0.1 #param to control fusing motion and apperance dist
        self.min_area = 300 #use to filter small bboxs

        # 流输入修改为图片输入的过渡变量
        self.last_detect_result = None
        self.tracker_class = None
        self.model_class = None


    def init_tracker(self):
        # 一会这里也写一个
        self.tracker_class = TRACKER_DICT[self.tracker](self)

        if self.detector == 'yolov8':
            print(f"loading detector {self.detector} checkpoint {self.detector_model_path}")
            self.model_class = YOLO(self.detector_model_path)
        else:
            print(f"detector {self.detector} is not supprted")
            exit(0)



    def yolov8_tracker(self, srcImage):

        frame = srcImage
        switch = 0 #这里逻辑没想好
        h, w, _ = frame.shape
        results = {}
        ids = []

        # Prepare the image for the detector
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img, (self.img_size, self.img_size))
        img_tensor = torch.from_numpy(img_resized).float().to(torch.device('cuda:0')).permute(2, 0, 1).unsqueeze(0) / 255.0


        # Get detector output
        with torch.no_grad():
            output = self.model_class.predict(img_tensor, conf=self.conf_thresh, iou=self.nms_thresh, classes=0, verbose=False)


        # Postprocess output to original scales
        output = postprocess_yolov8(output)                     #output才是bboxes
        detect_num = output.numel() // 6

        # Convert to tlwh format and update tracker
        if detect_num == 0: # 如果检测器没有检测到目标...
            # print("没找到，目前的处理是不处理，显示原图")
            outputs = None
            # outputs = self.last_detect_result
        elif self.tracker_class == None:
            outputs = None
            print("未初始化跟踪器")
        else:
            if isinstance(output, torch.Tensor):
                output = output.detach().cpu().numpy()
            output[:, 2] -= output[:, 0]
            output[:, 3] -= output[:, 1]

            outputs = self.tracker_class.update(output, img, frame)
            self.last_detect_result = outputs
            switch = 1
        
        if(switch):
            # Draw results on the frame
            for trk in outputs:
                bbox = trk.tlwh
                id = trk.track_id
                ids.append(id)
                cls = trk.category
                score = trk.score
                
                bbox[0] = int(bbox[0] * w / self.img_size)
                bbox[1] = int(bbox[1] * h / self.img_size)
                bbox[2] = int(bbox[2] * w / self.img_size)
                bbox[3] = int(bbox[3] * h / self.img_size)
                x_center = int(bbox[0] + bbox[2] / 2)
                y_center = int(bbox[1] + bbox[3] / 2)
                bbox[2]=int(bbox[0] + bbox[2])
                bbox[3]=int(bbox[1] + bbox[3])
                results[id] = bbox

                

        # print("detect_num\t", detect_num)
        return detect_num, results, torch.Tensor(ids)