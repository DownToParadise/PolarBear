import sys, os
import numpy as np
import torch
import cv2
from PIL import Image

# trackers
from trackers.byte_tracker import ByteTracker
from trackers.sort_tracker import SortTracker
from trackers.botsort_tracker import BotTracker
from trackers.c_biou_tracker import C_BIoUTracker
from trackers.deepsort_tracker import DeepSortTracker
from trackers.basetrack import BaseTrack, TrackState

from trackers.tracklet import Tracklet, Tracklet_w_velocity
from trackers.matching import *
from cython_bbox import bbox_overlaps as bbox_ious


# YOLOv8 modules
try:
    from ultralytics import YOLO
    from yolov8_utils.postprocess import postprocess as postprocess_yolov8

except Exception as e:
    print('Load yolov8 fail. If you want to use yolov8, please check the installation.')
    pass


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


        self.detector_model_path= './weights/yolov8n.pt'
        self.reid_model_path = './weights/ckpt.t700'
        self.dhn_path = './weights/DHN.pth'

        self.discard_reid = False #discard reid model, only work in bot-sort etc. which need a reid part
        self.track_buffer = 100
        self.gamma =0.1 #param to control fusing motion and apperance dist
        self.min_area = 300 #use to filter small bboxs

        # parser.add_argument('--save_images', action='store_true', help='save tracking results (image)')
        # parser.add_argument('--save_videos', action='store_true', help='save tracking results (video)')

        self.track_eval = True #Use TrackEval to evaluate

        self.frame_id = 0
        self.last_detect_result = None




    def yolov8_tracker(self,srcImage,dstImage):

        cuda = self.device != 'cpu' and torch.cuda.is_available()
        device = torch.device('cuda:0' if cuda else 'cpu')

        tracker = TRACKER_DICT[self.tracker](self, frame_id=self.frame_id)

        model = YOLO(self.detector_model_path)
        frame = srcImage
        dstImage = frame   #在这里加个背景

        h, w, _ = frame.shape

        # Prepare the image for the detector
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img, (self.img_size, self.img_size))
        img_tensor = torch.from_numpy(img_resized).float().to(device).permute(2, 0, 1).unsqueeze(0)
        #方形还是准
        # img_tensor = torch.from_numpy(img).float().to(device).permute(2, 0, 1).unsqueeze(0)

        # Get detector output
        with torch.no_grad():
            output = model.predict(img_tensor, conf=self.conf_thresh, iou=self.nms_thresh, classes=0)



        # Postprocess output to original scales
        output = postprocess_yolov8(output)    # 在这里用一下最小面积把


        # print("after:  ", output)
        if output.numel() == 0: # 如果检测器没有检测到目标...
            print("没找到，目前的处理是跳过")
            frame = dstImage
            outputs = self.last_detect_result

        else:

            # Convert to tlwh format and update tracker
            if isinstance(output, torch.Tensor):
                output = output.detach().cpu().numpy()
            output[:, 2] -= output[:, 0]
            output[:, 3] -= output[:, 1]

            outputs = tracker.update(output, img, frame)
            self.last_detect_result = outputs


        # Draw results on the frame
        for trk in outputs:
            bbox = trk.tlwh
            id = trk.track_id
            cls = trk.category
            score = trk.score

            bbox[0] = int(bbox[0] * w / self.img_size)
            bbox[1] = int(bbox[1] * h / self.img_size)
            bbox[2] = int(bbox[2] * w / self.img_size)
            bbox[3] = int(bbox[3] * h / self.img_size)

            x_center = int(bbox[0] + bbox[2] / 2)
            y_center = int(bbox[1] + bbox[3] / 2)


            # Draw the bounding box
            cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])),
                          (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])),
                          (255, 0, 0), 2)
            cv2.putText(frame, f'ID: {id}', (int(bbox[0]), int(bbox[1] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            cv2.circle(frame, (x_center, y_center), 2, (0, 255, 0), -1)
            print(f'ID: {id},  score: {score}')

        frame = dstImage

        cv2.imshow('Real-time Tracking', dstImage)

        return dstImage

