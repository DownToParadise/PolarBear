"""
main code for track
"""
import sys, os
import numpy as np
import torch
import cv2 
from PIL import Image
from tqdm import tqdm
import yaml 

from loguru import logger 
import argparse

from tracking_utils.envs import select_device
from tracking_utils.tools import *

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

def get_args():
    
    parser = argparse.ArgumentParser()

    """general"""

    parser.add_argument('--detector', type=str, default='yolov8', help='yolov7, yolox, etc.')
    parser.add_argument('--tracker', type=str, default='sort', help='sort, deepsort, etc')
    parser.add_argument('--reid_model', type=str, default='osnet_x0_25', help='osnet or deppsort')

    parser.add_argument('--kalman_format', type=str, default='default', help='use what kind of Kalman, sort, deepsort, byte, etc.')
    parser.add_argument('--img_size', type=int, default=1280, help='image size, [h, w]')

    parser.add_argument('--conf_thresh', type=float, default=0.2, help='filter tracks')
    parser.add_argument('--nms_thresh', type=float, default=0.7, help='thresh for NMS')
    parser.add_argument('--iou_thresh', type=float, default=0.5, help='IOU thresh to filter tracks')

    parser.add_argument('--device', type=str, default='0', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')

    """yolox"""
    parser.add_argument('--num_classes', type=int, default=1)
    parser.add_argument('--yolox_exp_file', type=str, default='./tracker/yolox_utils/yolox_m.py')

    """model path"""
    parser.add_argument('--detector_model_path', type=str, default='./weights/best.pt', help='model path')
    parser.add_argument('--trace', type=bool, default=False, help='traced model of YOLO v7')
    # other model path
    parser.add_argument('--reid_model_path', type=str, default='./weights/osnet_x0_25.pth', help='path for reid model path')
    parser.add_argument('--dhn_path', type=str, default='./weights/DHN.pth', help='path of DHN path for DeepMOT')

   
    """other options"""
    parser.add_argument('--discard_reid', action='store_true', help='discard reid model, only work in bot-sort etc. which need a reid part')
    parser.add_argument('--track_buffer', type=int, default=30, help='tracking buffer')
    parser.add_argument('--gamma', type=float, default=0.1, help='param to control fusing motion and apperance dist')
    parser.add_argument('--min_area', type=float, default=150, help='use to filter small bboxs')
    
    parser.add_argument('--track_eval', type=bool, default=True, help='Use TrackEval to evaluate')

    return parser.parse_args()

def main(args):
    
    """1. set some params"""


    """2. load detector"""
    device = select_device(args.device)


    if args.detector == 'yolov8':

        logger.info(f"loading detector {args.detector} checkpoint {args.detector_model_path}")
        model = YOLO(args.detector_model_path)

        model_img_size = [None, None]  
        stride = None 

        logger.info("loaded checkpoint done")

    else:
        logger.error(f"detector {args.detector} is not supprted")
        exit(0)

    """3. load sequences"""

    cap = cv2.VideoCapture(1)  # 0 for the default camera
    if not cap.isOpened():
        logger.error("Cannot open camera")
        exit(0)

    tracker = TRACKER_DICT[args.tracker](args)
    process_bar = tqdm(total=390, ncols=150)  # Initialize progress bar (for real-time, we won't know total)

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to capture frame from camera")
            break

        # Prepare the image for the detector
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img, (args.img_size, args.img_size))
        img_tensor = torch.from_numpy(img_resized).float().to(device).permute(2, 0, 1).unsqueeze(0)

        # Get detector output
        with torch.no_grad():
            output = model.predict(img_tensor, conf=args.conf_thresh, iou=args.nms_thresh,classes=0)

        # Postprocess output to original scales
        output = postprocess_yolov8(output)

        # Convert to tlwh format and update tracker
        if isinstance(output, torch.Tensor): 
            output = output.detach().cpu().numpy()
        output[:, 2] -= output[:, 0]
        output[:, 3] -= output[:, 1]
        current_tracks = tracker.update(output, img, frame)

        # Draw results on the frame
        for trk in current_tracks:
            bbox = trk.tlwh
            id = trk.track_id
            cls = trk.category
            score = trk.score

            if bbox[2] * bbox[3] > args.min_area:
                # Draw the bounding box
                cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), 
                              (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])), 
                              (255, 0, 0), 2)
                cv2.putText(frame, f'ID: {id}', (int(bbox[0]), int(bbox[1] - 10)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                print(f'ID: {id}, bbox: {bbox}, cls: {cls}, score: {score}')
        # Display the frame
        cv2.imshow('Real-time Tracking', frame)

        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        process_bar.update(1)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':

    args = get_args()
        
    main(args)
