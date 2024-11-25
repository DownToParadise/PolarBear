import cv2
 
cap = cv2.VideoCapture(0)  # 0表示获取默认摄像头
 
if not cap.isOpened():
    print("无法打开摄像头")
else:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法获取帧")
            break
        
        # 处理帧
        
        cv2.imshow("Frame", frame)
        if cv2.waitKey(1) == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()