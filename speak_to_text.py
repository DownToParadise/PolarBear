import wave  
import pyaudio  
from tqdm import *
import json
import base64
from urllib.request import urlopen
from urllib.request import Request
from urllib.error import URLError
from urllib.parse import urlencode


class BaiDu:

    def __init__(self, wave_out_path, record_second, API_KEY, SECRET_KEY, TOKEN_URL, ASR_URL, DEV_PID, CUID):
        self.wave_out_path = wave_out_path
        self.record_second = record_second
        self.API_KEY = API_KEY
        self.SECRET_KEY = SECRET_KEY
        self.TOKEN_URL = TOKEN_URL
        self.ASR_URL = ASR_URL
        self.DEV_PID = DEV_PID
        self.CUID = CUID

    def record_audio(self):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
        wf = wave.open(self.wave_out_path, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        print("* recording")
        for i in tqdm(range(0, int(RATE / CHUNK * self.record_second))):
            data = stream.read(CHUNK)
            wf.writeframes(data)
        print("* done recording")
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf.close()

    def fetch_token(self):
        params = {'grant_type': 'client_credentials',
                  'client_id': self.API_KEY,
                  'client_secret': self.SECRET_KEY}
        post_data = urlencode(params)
        post_data = post_data.encode( 'utf-8')
        req = Request(self.TOKEN_URL, post_data)
        try:
            f = urlopen(req)
            result_str = f.read()
        except URLError as err:
            print('token http response http code : ' + str(err.code))
            result_str = err.read()
        result_str =  result_str.decode()
        # print(result_str)
        result = json.loads(result_str)
        # print(result)
        print(result['scope'])
        return result['access_token']

    def DemoError(Exception):
        pass

    def BaiDuAPI(self):
        RATE = 16000
        FORMAT = self.wave_out_path[-3:]
        self.record_audio()
        token = self.fetch_token()
        speech_data = []
        with open(self.wave_out_path, 'rb') as speech_file:
            speech_data = speech_file.read()
        length = len(speech_data)
    
        speech = base64.b64encode(speech_data)
        speech = str(speech, 'utf-8')
        params = {'dev_pid': self.DEV_PID,
                'format': FORMAT,
                'rate': RATE,
                'token': token,
                'cuid': self.CUID,
                'channel': 1,
                'speech': speech,
                'len': length
                }
        post_data = json.dumps(params, sort_keys=False)
        # print post_data
        req = Request(self.ASR_URL, post_data.encode('utf-8'))
        req.add_header('Content-Type', 'application/json')
        try:
            f = urlopen(req)
            result_str = f.read()
        except URLError as err:
            print('asr http response http code : ' + str(err.code))
            result_str = err.read()
        result_str = str(result_str, 'u1tf-8')
        print(result_str)
        final = str(json.loads(result_str)['result'])[2:-2].split("。")
        final_order = "".join(final)
        return final_order



if __name__ == '__main__':
    API_KEY = 'TSfKh4ExpfSXyIH2MGI3k3s0'
    SECRET_KEY = 'TE6BZ1wLEMDCynkqHui7ITqMVwiMHe8A'
    wave_out_path = 'output.wav'
    FORMAT = wave_out_path[-3:]
    CUID = '123456PYTHON'
    DEV_PID = 1537  
    ASR_URL = 'http://vop.baidu.com/server_api'
    TOKEN_URL = 'http://aip.baidubce.com/oauth/2.0/token'
    record_second = 3
    BaiDu = BaiDu(wave_out_path, record_second, API_KEY, SECRET_KEY, TOKEN_URL, ASR_URL, DEV_PID, CUID)
    text = BaiDu.BaiDuAPI()
    print(text)




