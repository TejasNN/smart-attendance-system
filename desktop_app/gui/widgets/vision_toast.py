from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer


class VisionToast(QLabel):
    def __init__(self, parent, text: str, color="info", duration=2500):
        super().__init__(parent)

        colors = {
            "success": "rgba(46, 204, 113, 220)",
            "error": "rgba(231, 76, 60, 220)",
            "info": "rgba(52, 152, 219, 220)"
        }

        self.setText(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)

        self.setStyleSheet(f"""
            QLabel {{
                background-color: {colors.get(color, colors["info"])};
                color: white;
                padding: 10px 20px;
                border-radius: 16px;
                font-size: 15px;
                font-weight: 600;
            }}
        """)

        self.adjustSize()

        parent_w = parent.width()
        x = (parent_w - self.width()) // 2
        self.move(x, 60)

        # ---- floating opacity ----
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)

        # ---- fade in animation ----
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(450)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        # ---- gentle pop scale using position trick ----
        start_pos = QPoint(x, 40)
        end_pos = QPoint(x, 60)

        self.float_anim = QPropertyAnimation(self, b"pos")
        self.float_anim.setDuration(450)
        self.float_anim.setStartValue(start_pos)
        self.float_anim.setEndValue(end_pos)
        self.float_anim.setEasingCurve(QEasingCurve.Type.OutBack)

        self.show()
        self.raise_()

        self.fade_in.start()
        self.float_anim.start()

        # schedule fade out
        QTimer.singleShot(duration, self.fade_out)

    def fade_out(self):
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(600)
        self.fade_anim.setStartValue(1)
        self.fade_anim.setEndValue(0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_anim.finished.connect(self.deleteLater)
        self.fade_anim.start()
