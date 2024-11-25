# coding=utf-8
import os
import platform
import tkinter
from tkinter import *
from HCNetSDK import *
from PlayCtrl import *
from time import sleep
import sys
sys.path.append("/home/yeung/code/mmaction2-main")

class Camera:
    def __init__(self): 
    # 登录的设备信息
        self.DEV_IP = create_string_buffer(b'219.216.72.149')
        self.DEV_PORT = 8000
        self.DEV_USER_NAME = create_string_buffer(b'admin')
        self.DEV_PASSWORD = create_string_buffer(b'DING123456')

        self.WINDOWS_FLAG = False
        self.win = None  # 预览窗口
        self.funcRealDataCallBack_V30 = None  # 实时预览回调函数，需要定义为全局的

        self.PlayCtrl_Port = c_long(-1)  # 播放句柄
        self.Playctrldll = None  # 播放库
        self.FuncDecCB = None   # 播放库解码回调函数，需要定义为全局的
        self.Objdll = None     # 读取的函数库
        self.lUserId = None     # 设备登录返回的登录码

        self.lChannel = 1     # 该类使用的是不启用预览的云台控制（预连接），需要给出信道

        self.CameraLogin()

    # 获取当前系统环境
    def GetPlatform(self):
        sysstr = platform.system()
        print('' + sysstr)
        if sysstr != "Windows":
            self.WINDOWS_FLAG = False

    def SetSDKInitCfg(self):
        # 设置HCNetSDKCom组件库和SSL库加载路径
        # print(os.getcwd())
        if self.WINDOWS_FLAG:
            strPath = os.getcwd().encode('gbk')
            sdk_ComPath = NET_DVR_LOCAL_SDK_PATH()
            sdk_ComPath.sPath = strPath
            self.Objdll.NET_DVR_SetSDKInitCfg(2, byref(sdk_ComPath))
            self.Objdll.NET_DVR_SetSDKInitCfg(3, create_string_buffer(strPath + b'\libcrypto-1_1-x64.dll'))
            self.Objdll.NET_DVR_SetSDKInitCfg(4, create_string_buffer(strPath + b'\libssl-1_1-x64.dll'))
        else:
            strPath = os.getcwd().encode('utf-8')
            sdk_ComPath = NET_DVR_LOCAL_SDK_PATH()
            sdk_ComPath.sPath = strPath
            self.Objdll.NET_DVR_SetSDKInitCfg(2, byref(sdk_ComPath))
            self.Objdll.NET_DVR_SetSDKInitCfg(3, create_string_buffer(strPath + b'/libcrypto.so.1.1'))
            self.Objdll.NET_DVR_SetSDKInitCfg(4, create_string_buffer(strPath + b'/libssl.so.1.1'))

    def LoginDev(self):
        # 登录注册设备
        device_info = NET_DVR_DEVICEINFO_V30()
        self.lUserId = self.Objdll.NET_DVR_Login_V30(self.DEV_IP, self.DEV_PORT, self.DEV_USER_NAME, self.DEV_PASSWORD, byref(device_info))
        return (self.lUserId, device_info)

    def CameraLogin(self):
        # 获取系统平台
        self.GetPlatform()

        # 加载库,先加载依赖库
        if self.WINDOWS_FLAG:
            os.chdir(r'/home/yeung/code/mmaction2-main/lib/win')
            self.Objdll = ctypes.CDLL(r'./HCNetSDK.dll')  # 加载网络库
            Playctrldll = ctypes.CDLL(r'./PlayCtrl.dll')  # 加载播放库
        else:
            os.chdir(r'/home/yeung/code/mmaction2-main/lib/linux')
            self.Objdll = cdll.LoadLibrary(r'./libhcnetsdk.so')
            Playctrldll = cdll.LoadLibrary(r'./libPlayCtrl.so')

        self.SetSDKInitCfg()  # 设置组件库和SSL库加载路径    

        # 初始化DLL
        self.Objdll.NET_DVR_Init()
        # 启用SDK写日志
        self.Objdll.NET_DVR_SetLogToFile(3, bytes('./SdkLog_Python/', encoding="utf-8"), False)

        # 登录设备
        (lUserId, device_info) = self.LoginDev()
        if lUserId < 0:
            err = self.Objdll.NET_DVR_GetLastError()
            print('Login device fail, error code is: %d' % self.Objdll.NET_DVR_GetLastError())
            # 释放资源
            self.Objdll.NET_DVR_Cleanup()
            exit() 

    def CameraLogout(self):
        # 释放函数
        # 登出设备
        self.Objdll.NET_DVR_Logout(self.lUserId)

        # 释放资源
        self.Objdll.NET_DVR_Cleanup()

    def CameroLeftControl(self, sleeptime=2, speed=1):
        '''
        time: 最小运动时间0.6s，有时候0.6s也不会响应，第二次实验移动时间都会产生移动
        speed: 运动速度1~7, 角速度具体多少不清楚
        摄像头移动到边界如何判断
        移动到边界时，执行控制函数仍然返回移动为True
        '''
        lRet = self.Objdll.NET_DVR_PTZControlWithSpeed_Other(self.lUserId, self.lChannel, PAN_LEFT, 0, speed)
        if lRet == 0:
            print ('Start ptz control fail, error code is: %d' % self.Objdll.NET_DVR_GetLastError())
        else:
            print ('Start ptz control success')

        sleep(sleeptime)  
        
        lRet = self.Objdll.NET_DVR_PTZControlWithSpeed_Other(self.lUserId, self.lChannel, PAN_LEFT, 1, speed)
        if lRet == 0:
            print ('Start ptz control fail, error code is: %d' % self.Objdll.NET_DVR_GetLastError())
        else:
            print ('Start ptz control success')  

    def CameroRightControl(self, sleeptime=2, speed=1):
        lRet = self.Objdll.NET_DVR_PTZControlWithSpeed_Other(self.lUserId, self.lChannel, PAN_RIGHT, 0, speed)
        if lRet == 0:
            print ('Start ptz control fail, error code is: %d' % self.Objdll.NET_DVR_GetLastError())
        else:
            print ('Start ptz control success')

        sleep(sleeptime)  

        lRet = self.Objdll.NET_DVR_PTZControlWithSpeed_Other(self.lUserId, self.lChannel, PAN_RIGHT, 1, speed)
        if lRet == 0:
            print ('Start ptz control fail, error code is: %d' % self.Objdll.NET_DVR_GetLastError())
        else:
            print ('Start ptz control success')  
    
    # def __del__(self):
    #     self.CameraLogout()
    
    def NET_DVR_PTZControlWithSpeed_Other(self, command, sleeptime, speed=7):
        """
        实验摄像头只能上下左右移动，不能上左或上右移动，对角戏无法移动
        # 目的要让移动时间经可能的小，得出最小移动时间的速度为多少，就作为我们摄像头移动速度s
        # speed = 7 , time=0.3、0.2、0.15、0.1、0.05,可移动
        # speed = 5, time=0.05,可移动
        # 第二次实验的出结论，时间很小0.1s也可以移动
        """

        # 参数判定
        if type(command) is str:
            command = eval(command)
            print(command)
        print("commad type is" + str(type(command)))  
        
        if(speed<1 or speed>7):
            print("the speed should in 1~7")
            return 0
        
        print("cam move time is\t" + str(sleeptime))

        # 运动执行
        lRet = self.Objdll.NET_DVR_PTZControlWithSpeed_Other(self.lUserId, self.lChannel, command, 0, speed)
        if lRet == 0:
            print ('Start ptz control fail, error code is: %d' % self.Objdll.NET_DVR_GetLastError())
        else:
            print ('Start ptz control success')  

        sleep(sleeptime)

        lRet = self.Objdll.NET_DVR_PTZControlWithSpeed_Other(self.lUserId, self.lChannel, command, 1, speed)
        if lRet == 0:
            print ('Start ptz control fail, error code is: %d' % self.Objdll.NET_DVR_GetLastError())
        else:
            print ('Start ptz control success')

        return lRet
