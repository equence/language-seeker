from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont  # 新增：导入 QFont

class AboutWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("关于")
        self.setFixedSize(200, 100)
        layout = QVBoxLayout()
        label = QLabel("language-seeker\n版本 0.1 Alpha\n\n")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("微软雅黑", 10))  # 新增：设置字体为“微软雅黑”
        layout.addWidget(label)
        self.setLayout(layout)
