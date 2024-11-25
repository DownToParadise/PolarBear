import cv2
import os

def create_video_from_images(image_folder, output_video, fps=30):
    # 获取文件夹中的所有图像文件
    images = [img for img in os.listdir(image_folder) if img.endswith((".png", ".jpg", ".jpeg"))]
    images.sort()  # 确保按顺序读取文件

    # 读取第一张图像以获取视频尺寸
    first_image_path = os.path.join(image_folder, images[0])
    frame = cv2.imread(first_image_path)
    height, width, layers = frame.shape

    # 定义视频编码器和创建视频对象
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

    # 遍历所有图像并写入视频
    for image in images:
        image_path = os.path.join(image_folder, image)
        frame = cv2.imread(image_path)
        video.write(frame)

    # 释放视频对象
    video.release()

# 使用示例
image_folder = 'track_demo_results/vis_results/'
output_video = 'test7_output.mp4'
create_video_from_images(image_folder, output_video)