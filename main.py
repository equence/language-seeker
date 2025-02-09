import sys
import requests
import json
import keyboard
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, 
                            QWidget, QLabel, QVBoxLayout)
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QColor, QPainter, QBrush, QCursor
from PIL import ImageGrab
import pytesseract
import pyautogui
import hashlib
from image_window import ImageWindow
from region_selector import RegionSelector  # 新增导入
from ocr_worker import OCRWorker
import os
import configparser

# 配置信息（需要用户自己填写）
BAIDU_APP_ID = '20250208002268787'
BAIDU_SECRET_KEY = '0L7Q4x4UUEz5XDO9x5lt'


class TranslationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.thread = None  # 新增：初始化线程属性
        self.config_path = os.path.join(os.path.dirname(__file__), "config.ini")
        self.capture_region = self.load_config()  # 加载保存的区域或使用默认值
        self.ocr_running = False  # 新增：防止重复OCR调用导致卡顿
        self.initUI()
        self.setupHotkeys()
        # 新增：注册手动区域截图的快捷键
        keyboard.add_hotkey('ctrl+shift+a', self.manual_capture)
        # 新增：创建图像显示窗口
        self.image_window = ImageWindow()
        self.image_window.show()
        
        # 定时器检查新消息
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_messages)
        self.timer.start(2000)  # 2秒检查一次
        self.threads = []  # 新增：保存启动的线程引用

    def load_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_path):
            config.read(self.config_path)
            try:
                left = int(config.get("capture_region", "left"))
                top = int(config.get("capture_region", "top"))
                right = int(config.get("capture_region", "right"))
                bottom = int(config.get("capture_region", "bottom"))
                # 读取源语言设定，缺省为 English
                source_lang = config.get("settings", "source_lang", fallback="en")
                self.source_lang = source_lang
                return (left, top, right, bottom)
            except Exception:
                pass
        # 默认值
        self.source_lang = "en"
        return (100, 100, 400, 300)
        
    def save_config(self):
        config = configparser.ConfigParser()
        config["capture_region"] = {
            "left": str(self.capture_region[0]),
            "top": str(self.capture_region[1]),
            "right": str(self.capture_region[2]),
            "bottom": str(self.capture_region[3])
        }
        config["settings"] = {
            "source_lang": self.source_lang
        }
        with open(self.config_path, "w") as configfile:
            config.write(configfile)

    def initUI(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout()
        self.label = QLabel("翻译内容将显示在这里")
        self.label.setFont(QFont("微软雅黑", 10))
        self.label.setStyleSheet("color: white; background-color: rgba(0,0,0,150); padding: 10px;")
        layout.addWidget(self.label)
        
        self.setLayout(layout)
        self.setGeometry(300, 300, 300, 150)
        self.setMouseTracking(True)  # 新增：启用鼠标跟踪
        self.initDrag()  # 设置鼠标跟踪判断默认值
        self.dragging = False
        self.resizing = False           # 新增：是否处于调整大小状态
        self.resize_offset = None       # 新增：保存初始鼠标位置
        self.orig_size = None           # 新增：保存窗口初始尺寸
        self.setMinimumSize(150, 100)    # 新增：设置窗口最小尺寸
        self.offset = QPoint()

    def initDrag(self):
        # 设置鼠标跟踪判断扳机默认值
        self._move_drag = False
        self._corner_drag = False
        self._bottom_drag = False
        self._right_drag = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 如果鼠标在右下角10px范围内，则进入调整大小模式
            if event.pos().x() >= self.width() - 10 and event.pos().y() >= self.height() - 10:
                self.resizing = True
                self.resize_offset = self.mapToGlobal(event.pos())
                self.orig_size = self.size()
            else:
                self.dragging = True
                self.offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self.resizing:
            new_global_pos = self.mapToGlobal(event.pos())
            delta = new_global_pos - self.resize_offset
            new_width = max(self.orig_size.width() + delta.x(), self.minimumWidth())
            new_height = max(self.orig_size.height() + delta.y(), self.minimumHeight())
            self.resize(new_width, new_height)
        elif self.dragging:
            self.move(event.globalPos() - self.offset)
        else:
            # 根据鼠标位置改变游标样式
            if event.pos().x() >= self.width() - 10 and event.pos().y() >= self.height() - 10:
                self.setCursor(Qt.SizeFDiagCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False
        self.setCursor(Qt.ArrowCursor)

    def setupHotkeys(self):
        keyboard.add_hotkey('ctrl+enter', self.translate_input)
        # 新增：注册手动区域截图的快捷键
        keyboard.add_hotkey('ctrl+shift+s', self.manual_capture)

    def translate_input(self):
        # 修改：输入文本翻译方向为：中文 → 目标语言（由源语言选项决定）
        chinese_text = "你好"  # 实际应获取输入内容
        if self.source_lang == "en":
            translated = self.translate_baidu(chinese_text, 'en', 'zh')
        else:  # self.source_lang == "kor"
            translated = self.translate_baidu(chinese_text, 'kor', 'zh')
        self.simulate_keyboard(translated)

    def check_messages(self):
        # 删除了调试输出
        self.capture_underlying()
    
    def get_valid_bbox(self, bbox):
        # 限制 bbox 在屏幕范围内
        import pyautogui
        sw, sh = pyautogui.size()
        left, top, right, bottom = bbox
        left = max(0, left)
        top = max(0, top)
        right = min(sw, right)
        bottom = min(sh, bottom)
        return (left, top, right, bottom)
        
    def capture_underlying(self):
        from PyQt5.QtCore import QThread
        thread = QThread()
        self.threads.append(thread)  # 保存线程引用
        worker = OCRWorker(self.capture_region, self.source_lang, self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        thread.worker = worker  # 保持对 worker 的引用，避免被垃圾回收
        # 当线程完成后移除引用并自动删除线程
        thread.finished.connect(lambda: self.threads.remove(thread))
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def handle_ocr_finished(self, translation, img):
        self.label.setText(translation)
        if img:
            self.image_window.update_image(img)

    def manual_capture(self):
        # 使用单次定时器安排在主线程中启动区域选择器
        QTimer.singleShot(0, self._show_region_selector)

    def _show_region_selector(self):
        self.selector = RegionSelector()
        self.selector.regionSelected.connect(self.handle_region_selected)

    def handle_region_selected(self, rect):
        if (rect.left() == rect.right() or rect.top() == rect.bottom()):
            return
        self.capture_region = (rect.left(), rect.top(), rect.right(), rect.bottom())
        self.save_config()
        left, top, right, bottom = self.capture_region
        left, top, right, bottom = self.get_valid_bbox((left, top, right, bottom))
        img = ImageGrab.grab(bbox=(left, top, right, bottom))
        ocr_lang = "eng" if self.source_lang == "en" else "kor"
        text = pytesseract.image_to_string(img, lang=ocr_lang)
        if text.strip():
            lines = text.strip().splitlines()
            translations = []
            for line in lines:
                if line.strip():
                    tr = self.translate_baidu(line.strip(), 'zh', 'en') if self.source_lang == "en" else self.translate_baidu(line.strip(), 'zh', 'kor')
                    translations.append(tr)
            display_text = "\n".join(translations)
        else:
            display_text = ""
        self.label.setText(display_text)
        self.image_window.update_image(img)

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
        response = requests.get(url, params=params)
        result = json.loads(response.text)
        if 'trans_result' in result:
            return result['trans_result'][0]['dst']
        else:
            return result.get('error_msg', '翻译错误')

    def simulate_keyboard(self, text):
        # 使用pyautogui模拟键盘输入
        pyautogui.write(text, interval=0.05)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 系统托盘图标
    tray = QSystemTrayIcon()
    tray.setIcon(QIcon('icon.png'))
    tray.setVisible(True)
    
    menu = QMenu()
    exit_action = menu.addAction("退出")
    exit_action.triggered.connect(app.quit)
    
    # 创建源语言子菜单
    lang_menu = QMenu("源语言")
    english_action = lang_menu.addAction("英语")
    korean_action = lang_menu.addAction("韩语")
    english_action.setCheckable(True)
    korean_action.setCheckable(True)
    # 新增：根据加载的配置设置右键菜单当前选项
    # window 已在下方创建之前加载ini配置
    window = TranslationWindow()
    if window.source_lang == "en":
        english_action.setChecked(True)
        korean_action.setChecked(False)
    else:
        english_action.setChecked(False)
        korean_action.setChecked(True)
    
    def set_language(lang):
        window.source_lang = lang
        english_action.setChecked(lang == "en")
        korean_action.setChecked(lang == "kor")
        window.save_config()  # 保存选择的语言
        
    english_action.triggered.connect(lambda: set_language("en"))
    korean_action.triggered.connect(lambda: set_language("kor"))
    
    menu.addMenu(lang_menu)
    menu.addAction(exit_action)
    
    # 使用 tray.setContextMenu() 后，不需额外连接 tray.activated 信号
    tray.setContextMenu(menu)
    # 移除 on_tray_activated 相关代码以降低卡顿
    
    window.show()
    sys.exit(app.exec_())