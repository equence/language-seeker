from PyQt5.QtWidgets import QWidget, QRubberBand
from PyQt5.QtCore import QRect, QPoint, pyqtSignal, Qt

class RegionSelector(QWidget):
    regionSelected = pyqtSignal(QRect)
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.setWindowOpacity(0.3)
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = QPoint()
        self.show()

    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rubberBand.setGeometry(QRect(self.origin, self.origin))
        self.rubberBand.show()

    def mouseMoveEvent(self, event):
        rect = QRect(self.origin, event.pos()).normalized()
        self.rubberBand.setGeometry(rect)

    def mouseReleaseEvent(self, event):
        self.rubberBand.hide()
        rect = self.rubberBand.geometry()
        # 修改：将本地坐标转换为全局坐标
        global_top_left = self.mapToGlobal(rect.topLeft())
        global_bottom_right = self.mapToGlobal(rect.bottomRight())
        global_rect = QRect(global_top_left, global_bottom_right)
        self.regionSelected.emit(global_rect)
        self.close()
