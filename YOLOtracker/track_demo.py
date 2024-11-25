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

def get_args():
    
    parser = argparse.ArgumentParser()

    """general"""
    parser.add_argument('--obj', type=str, required=True, default='../test7.mp4', help='video or images folder PATH')

    parser.add_argument('--detector', type=str, default='yolov8', help='yolov7, yolox, etc.')
    parser.add_argument('--tracker', type=str, default='sort', help='sort, deepsort, etc')
    parser.add_argument('--reid_model', type=str, default='deepsort', help='osnet or deppsort')

    parser.add_argument('--kalman_format', type=str, default='default', help='use what kind of Kalman, sort, deepsort, byte, etc.')
    parser.add_argument('--img_size', type=int, default=1280, help='image size, [h, w]')

    parser.add_argument('--conf_thresh', type=float, default=0.5, help='filter tracks')
    parser.add_argument('--nms_thresh', type=float, default=0.3, help='thresh for NMS')
    parser.add_argument('--iou_thresh', type=float, default=0.3, help='IOU thresh to filter tracks')

    parser.add_argument('--device', type=str, default='0', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')

    """model path"""
    parser.add_argument('--detector_model_path', type=str, default='./weights/yolov8n.pt', help='model path')
    #pose效果最好，这是我没想到的
    parser.add_argument('--trace', type=bool, default=False, help='traced model of YOLO v7')
    # other model path
    parser.add_argument('--reid_model_path', type=str, default='./weights/ckpt.t7', help='path for reid model path')
    parser.add_argument('--dhn_path', type=str, default='../weights/DHN.pth', help='path of DHN path for DeepMOT')

   
    """other options"""
    parser.add_argument('--discard_reid', action='store_true', help='discard reid model, only work in bot-sort etc. which need a reid part')
    parser.add_argument('--track_buffer', type=int, default=150, help='tracking buffer')
    parser.add_argument('--gamma', type=float, default=0.1, help='param to control fusing motion and apperance dist')
    parser.add_argument('--min_area', type=float, default=150, help='use to filter small bboxs')

    parser.add_argument('--save_dir', type=str, default='track_demo_results')
    parser.add_argument('--save_images', action='store_true', help='save tracking results (image)')
    parser.add_argument('--save_videos', action='store_true', help='save tracking results (video)')
    
    parser.add_argument('--track_eval', type=bool, default=True, help='Use TrackEval to evaluate')

    return parser.parse_args()

def tracker(args):
    
    """1. set some params"""

    # NOTE: if save video, you must save image
    if args.save_videos:
        args.save_images = True
        
    """2. load detector"""
    device = select_device(args.device)
    if args.detector == 'yolov8':
        logger.info(f"loading detector {args.detector} checkpoint {args.detector_model_path}")
        model = YOLO(args.detector_model_path)
        model_img_size = [None, None]  
        stride = None
        logger.info("loaded checkpoint done")

    else:
        logger.error(f"detector {args.detector} is not supported")
        exit(0)

    """3. load sequences"""

    dataset = DemoDataset(file_name=args.obj, img_size=model_img_size, model=args.detector, stride=stride, )
    data_loader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=False)

    tracker = TRACKER_DICT[args.tracker](args, )


    save_dir = args.save_dir

    process_bar = enumerate(data_loader)
    process_bar = tqdm(process_bar, total=len(data_loader), ncols=150)

    results = []

    """4. Tracking"""

    for frame_idx, (ori_img, img) in process_bar:
        if args.detector == 'yolov8':
            img = img.squeeze(0).cpu().numpy()

        else:
            img = img.to(device)  # (1, C, H, W)
            img = img.float() 

        ori_img = ori_img.squeeze(0)

        # get detector output 
        with torch.no_grad():
            if args.detector == 'yolov8':
                output = model.predict(img, conf=args.conf_thresh, iou=args.nms_thresh,classes=0)
            else:
                output = model(img)

        # postprocess output to original scales

        if args.detector == 'yolov8':
            output = postprocess_yolov8(output)
        
        else: raise NotImplementedError

        # output: (tlbr, conf, cls)
        # convert tlbr to tlwh
        if isinstance(output, torch.Tensor): 
            output = output.detach().cpu().numpy()
        output[:, 2] -= output[:, 0]
        output[:, 3] -= output[:, 1]
        #追踪器更新

        if(1):
            current_tracks = tracker.update(output, img, ori_img.cpu().numpy())
    
        # save results
        cur_tlwh, cur_id, cur_cls, cur_score = [], [], [], []
        for trk in current_tracks:
            bbox = trk.tlwh
            id = trk.track_id
            cls = trk.category
            score = trk.score

            # filter low area bbox
            if bbox[2] * bbox[3] > args.min_area:
                cur_tlwh.append(bbox)
                cur_id.append(id)
                cur_cls.append(cls)
                cur_score.append(score)
                # results.append((frame_id + 1, id, bbox, cls))

        results.append((frame_idx + 1, cur_id, cur_tlwh, cur_cls, cur_score))

        if args.save_images:
            plot_img(img=ori_img, frame_id=frame_idx, results=[cur_tlwh, cur_id, cur_cls], 
                        save_dir=os.path.join(save_dir, 'vis_results'))

    save_txt_results(folder_name=os.path.join(save_dir, 'txt_results'),
                    seq_name='demo', 
                    results=results)
    
    if args.save_videos:
        save_video(images_path=os.path.join(save_dir, 'vis_results'))
        logger.info(f'save video done')

if __name__ == '__main__':

    args = get_args()
        
    tracker(args)

    #为了把图像弄成视频加的函数
    from images2mp4 import *
    image_folder = 'track_demo_results/vis_results/'
    output_video = 'output_111.mp4'
    create_video_from_images(image_folder, output_video)
