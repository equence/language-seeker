from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

class ImageWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("截图预览")
        layout = QVBoxLayout()
        self.label = QLabel("图像预览")
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.resize(300, 200)
        
    def update_image(self, pil_image):
        # 将 PIL 图像转换为 RGB 格式
        rgb_image = pil_image.convert('RGB')
        width, height = rgb_image.size
        bytes_per_line = width * 3
        data = rgb_image.tobytes("raw", "RGB")
        qimage = QImage(data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        # 可选：缩放图像以适应标签显示区域
        scaled_pixmap = pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled_pixmap)
