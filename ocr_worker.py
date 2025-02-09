from PyQt5.QtCore import QObject, QMetaObject, Q_ARG, Qt, QTimer, QThread, pyqtSlot
import pytesseract
from PIL import ImageGrab
import pyautogui
import requests
import json
import hashlib

BAIDU_APP_ID = '20250208002268787'
BAIDU_SECRET_KEY = '0L7Q4x4UUEz5XDO9x5lt'

class OCRWorker(QObject):
    def __init__(self, capture_region, source_lang, main_window, parent=None):
        super().__init__(parent)
        self.capture_region = capture_region
        self.source_lang = source_lang
        self.main_window = main_window  # 新增：保存主窗口引用

    @pyqtSlot()  # 确保 run 可作为槽函数调用
    def run(self):
        try:
            # 限制 bbox 在屏幕范围内
            sw, sh = pyautogui.size()
            left, top, right, bottom = self.capture_region
            left = max(0, left)
            top = max(0, top)
            right = min(sw, right)
            bottom = min(sh, bottom)
            img = ImageGrab.grab(bbox=(left, top, right, bottom))
            ocr_lang = "eng" if self.source_lang == "en" else "kor"
            text = pytesseract.image_to_string(img, lang=ocr_lang)
            translation_lines = []
            if text.strip():
                for line in text.strip().splitlines():
                    if line.strip():
                        if self.source_lang == "en":
                            tr = self.translate_baidu(line.strip(), 'zh', 'en')
                        else:
                            tr = self.translate_baidu(line.strip(), 'zh', 'kor')
                        translation_lines.append(tr)
                translation = "\n".join(translation_lines)
            else:
                translation = ""
        except Exception as e:
            translation = "Error: " + str(e)
            img = None
        QTimer.singleShot(0, lambda: self.main_window.handle_ocr_finished(translation, img))
        
    def translate_baidu(self, text, target_lang, src_lang):
        url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
        salt = '12345'
        sign_str = BAIDU_APP_ID + text + salt + BAIDU_SECRET_KEY
        m = hashlib.md5()
        m.update(sign_str.encode('utf-8'))
        sign = m.hexdigest()
        params = {
            'q': text,
            'from': src_lang,
            'to': target_lang,
            'appid': BAIDU_APP_ID,
            'salt': salt,
            'sign': sign
        }
        # 设置超时时间为 5 秒，避免长时间阻塞
        try:
            response = requests.get(url, params=params, timeout=5)
            result = json.loads(response.text)
        except Exception as e:
            return "请求错误: " + str(e)
        if 'trans_result' in result:
            return result['trans_result'][0]['dst']
        else:
            return result.get('error_msg', '翻译错误')
