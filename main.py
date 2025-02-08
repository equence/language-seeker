import sys
import requests
import json
import keyboard
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, 
                            QWidget, QLabel, QVBoxLayout)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QIcon, QFont, QColor, QPainter, QBrush
from PIL import ImageGrab
import pytesseract
import pyautogui
import hashlib
from image_window import ImageWindow
from region_selector import RegionSelector  # 新增导入

# 配置信息（需要用户自己填写）
BAIDU_APP_ID = '20250208002268787'
BAIDU_SECRET_KEY = '0L7Q4x4UUEz5XDO9x5lt'


class TranslationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.capture_region = (100, 100, 400, 300)  # 新增：初始化截取区域
        self.initUI()
        self.setupHotkeys()
        # 新增：注册手动区域截图的快捷键
        keyboard.add_hotkey('ctrl+shift+s', self.manual_capture)
        # 新增：创建图像显示窗口
        self.image_window = ImageWindow()
        self.image_window.show()
        
        # 定时器检查新消息
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_messages)
        self.timer.start(2000)  # 2秒检查一次

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
        # 需要实现获取输入框内容的功能（可能需要使用Windows API）
        # 这里模拟翻译过程
        chinese_text = "你好"  # 实际应该获取输入框内容
        translated = self.translate_baidu(chinese_text, 'kor', 'zh')
        self.simulate_keyboard(translated)

    def check_messages(self):
        # 直接捕获窗口覆盖区域，无需隐藏窗口
        self.capture_underlying()
    
    def capture_underlying(self):
        # 使用实例属性 self.capture_region 而非固定全局变量
        left, top, right, bottom = self.capture_region
        img = ImageGrab.grab(bbox=(left, top, right, bottom))
        text = pytesseract.image_to_string(img, lang='eng')
        if text.strip():
            translation = self.translate_baidu(text, 'zh', 'en')
            display_text = "识别内容：\n" + text.strip() + "\n\n翻译：\n" + translation
        else:
            display_text = ""
        self.label.setText(display_text)
        self.image_window.update_image(img)

    def manual_capture(self):
        # 使用单次定时器安排在主线程中启动区域选择器
        QTimer.singleShot(0, self._show_region_selector)

    def _show_region_selector(self):
        self.selector = RegionSelector()
        self.selector.regionSelected.connect(self.handle_region_selected)

    def handle_region_selected(self, rect):
        # 更新截取区域为用户选择的全局区域
        self.capture_region = (rect.left(), rect.top(), rect.right(), rect.bottom())
        img = ImageGrab.grab(bbox=self.capture_region)
        text = pytesseract.image_to_string(img, lang='eng')
        if text.strip():
            translation = self.translate_baidu(text, 'zh', 'en')
            display_text = "识别内容：\n" + text.strip() + "\n\n翻译：\n" + translation
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
    tray.setContextMenu(menu)
    
    window = TranslationWindow()
    window.show()
    sys.exit(app.exec_())