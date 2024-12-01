"""带有优先级的人脸识别"""
import face_recognition
import numpy as np
import cv2

def face_re(goal_images, input_image):
    known_face_encodings = []
    known_face_names = []

    # 加载已知人脸图片并提取特征
    for goal_image in goal_images:
        known_image = face_recognition.load_image_file(goal_image)
        face_encoding = face_recognition.face_encodings(known_image)[0]
        known_face_encodings.append(face_encoding)
        known_face_names.append(goal_image.split('.')[0])  # 使用文件名作为名字

    # 加载未知人脸图片
    unknown_image = face_recognition.load_image_file(input_image)

    # 人脸检测
    face_locations = face_recognition.face_locations(unknown_image)
    # 人脸特征提取
    face_encodings = face_recognition.face_encodings(unknown_image, face_locations)

    # 转换为 OpenCV 格式的图像
    unknown_image_cv = cv2.cvtColor(unknown_image, cv2.COLOR_RGB2BGR)

    found = False  
    for name, encoding in zip(known_face_names, known_face_encodings):
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # 判断与已知人脸的匹配
            matches = face_recognition.compare_faces([encoding], face_encoding)
            
            if matches[0]:  # 如果有匹配成功
                # 为人脸画边界框
                cv2.rectangle(unknown_image_cv, (left, top), (right, bottom), (0, 0, 255), 2)
                # 在人脸边界框下方绘制该人脸所属人的名字
                cv2.rectangle(unknown_image_cv, (left, bottom - 20), (right, bottom), (0, 0, 255), cv2.FILLED)
                cv2.putText(unknown_image_cv, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                found = True  
                break  
        if found:  
            break

    if not found:  
        return -1

    # 使用 OpenCV 显示处理后的图像
    cv2.imshow("Processed Image", unknown_image_cv)
    cv2.waitKey(5000)  # 等待按键
    cv2.destroyAllWindows()  # 关闭窗口

if __name__ == '__main__':
    goal_images = ['1.png', '2.png', '3.png']  # 目标人脸图片
    input_image = 'input1.jpg'  # 输入的未知人脸图片
    result = face_re(goal_images, input_image)
    if result == -1:
        print("未找到任何目标人脸")