import sys, os
import numpy as np
import torch
import cv2
from PIL import Image

from loguru import logger
import argparse

from tracking_utils.envs import select_device
from tracking_utils.tools import *
from tracking_utils.visualization import plot_img, save_video
from tracker_dataloader import TestDataset, DemoDataset

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
    logger.warning(e)
    logger.warning('Load yolov8 fail. If you want to use yolov8, please check the installation.')
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
        self.obj=('../jin.mp4') #or camera

        self.detector = 'yolov8'
        self.tracker = 'ocsort'
        self.reid_model = 'deepsort'
        self.kalman_format = 'ocsort'
        self.img_size = 640
        self.device = '0'

        self.conf_thresh = 0.5
        self.nms_thresh = 0.3
        self.iou_thresh = 0.3


        self.detector_model_path= './weights/yolov8n.pt'
        self.reid_model_path = './weights/ckpt.t7'
        self.dhn_path = './weights/DHN.pth'

        self.discard_reid = False #discard reid model, only work in bot-sort etc. which need a reid part
        self.track_buffer = 100
        self.gamma =0.1 #param to control fusing motion and apperance dist
        self.min_area = 150 #use to filter small bboxs

        # parser.add_argument('--save_images', action='store_true', help='save tracking results (image)')
        # parser.add_argument('--save_videos', action='store_true', help='save tracking results (video)')

        self.track_eval = True #Use TrackEval to evaluate


        self.last_detect_result = None



    def yolov8_tracker(self):
        """1. set some params"""

        """2. load detector"""
        device = select_device(self.device)

        if self.detector == 'yolov8':

            logger.info(f"loading detector {self.detector} checkpoint {self.detector_model_path}")
            model = YOLO(self.detector_model_path)

            model_img_size = [None, None]
            stride = None

            logger.info("loaded checkpoint done")

        else:
            logger.error(f"detector {self.detector} is not supprted")
            exit(0)

        """3. load sequences"""

        if self.obj == 'camera':
            cap = cv2.VideoCapture(1)  # 0 for the default camera
            if not cap.isOpened():
                logger.error("Cannot open camera")
                exit(0)
        else:
            cap = cv2.VideoCapture(self.obj)  # 0 for the default camera
            if not cap.isOpened():
                logger.error(f"Cannot open video{self.obj}")
                exit(0)

        tracker = TRACKER_DICT[self.tracker](self)

        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to capture frame from camera")
                break

            h, w, _ = frame.shape

            # Prepare the image for the detector
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_resized = cv2.resize(img, (self.img_size, self.img_size))
            img_tensor = torch.from_numpy(img_resized).float().to(device).permute(2, 0, 1).unsqueeze(0)
            # img_tensor = torch.from_numpy(img).float().to(device).permute(2, 0, 1).unsqueeze(0)

            # Get detector output
            with torch.no_grad():
                output = model.predict(img_tensor, conf=self.conf_thresh, iou=self.nms_thresh, classes=0)
                #这种方形输入比原图输入更准确
                # output = model.predict(img, conf=self.conf_thresh, iou=self.nms_thresh, classes=0)

            # Postprocess output to original scales
            output = postprocess_yolov8(output)

            if output.numel() == 0: # 如果检测器没有检测到目标...
                print("111")
                cv2.imshow('Real-time Tracking', frame)
            else:

                # Convert to tlwh format and update tracker
                if isinstance(output, torch.Tensor):
                    output = output.detach().cpu().numpy()
                output[:, 2] -= output[:, 0]
                output[:, 3] -= output[:, 1]

                current_tracks = tracker.update(output, img, frame)
                self.last_detect_result = current_tracks

                # Draw results on the frame
                for trk in self.last_detect_result:
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

                    if bbox[2] * bbox[3] > self.min_area:
                        # Draw the bounding box
                        cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])),
                                      (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])),
                                      (255, 0, 0), 2)
                        cv2.putText(frame, f'ID: {id}', (int(bbox[0]), int(bbox[1] - 10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        cv2.circle(frame, (x_center, y_center), 2, (0, 255, 0), -1)
                        print(f'ID: {id},  score: {score}')

            # Display the frame
            cv2.imshow('Real-time Tracking', frame)

            # Break the loop on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    track = Tracker()
    track.yolov8_tracker()