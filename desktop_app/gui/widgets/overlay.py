from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QMovie, QFont


class ProvisioningOverlay(QFrame):
    cancel_requested = pyqtSignal()
    retry_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("provisionOverlay")
        self.setVisible(False)

        # TRUE MODAL BLOCK
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay, True)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Prevent animation GC
        self._active_animations = []

        self.setStyleSheet("""
        #provisionOverlay {
            background: rgba(255,255,255,200);
        }

        #glassCard {
            background: rgba(255,255,255,180);
            border-radius: 18px;
            border: 1px solid rgba(200,200,200,140);
        }

        QLabel {
            color:#111827;
        }

        QPushButton {
            padding: 9px 16px;
            border-radius: 8px;
            color:white;
            font-weight:700;
        }

        QPushButton#retryBtn {
            background:#2563eb;
        }

        QPushButton#cancelBtn {
            background:#ef4444;
        }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -------- Glass Card --------
        self.card = QFrame()
        self.card.setObjectName("glassCard")
        self.card.setMinimumWidth(420)
        self.card.setMaximumWidth(520)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(15)

        # -------- Title --------
        title = QLabel("Device Provisioning")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))

        # -------- Spinner --------
        self.spinner = QLabel()
        self.spinner.setStyleSheet("""
            QLabel {
                background: rgba(255,255,255,100);
                border-radius: 120px;
            }
        """)
        self.spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gif_path = "desktop_app/assets/icons/loader.gif"
        movie = QMovie(gif_path)
        movie.setScaledSize(QSize(220,220))
        self.spinner.setMovie(movie)
        self.movie = movie

        # -------- Status Message --------
        self.message = QLabel("Preparing device registration…")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.message.setWordWrap(True)
        self.message.setFont(QFont("Segoe UI", 12))
        self.message.setFixedHeight(60)   # keeps layout stable
        self.message.setMinimumWidth(380)

        # -------- Buttons --------
        btn_row = QHBoxLayout()

        self.btn_retry = QPushButton("Retry")
        self.btn_retry.setObjectName("retryBtn")

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancelBtn")

        btn_row.addWidget(self.btn_retry)
        btn_row.addWidget(self.btn_cancel)

        # -------- Feedback Toast --------
        self.feedback = QLabel(self)
        self.feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback.setVisible(False)

        card_layout.addWidget(title)
        card_layout.addWidget(self.spinner)
        card_layout.addWidget(self.message)
        card_layout.addLayout(btn_row)

        layout.addStretch()
        layout.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        # -------- Events --------
        self.btn_cancel.clicked.connect(lambda: self.cancel_requested.emit())
        self.btn_retry.clicked.connect(lambda: self.retry_requested.emit())

    # ---------- PUBLIC API ----------
    def show_overlay(self):
        parent = self.parentWidget()
        if parent:
            self.setGeometry(parent.rect())
            
        self.movie.start()
        self.show()
        self.raise_()
        self.setFocus()


    def hide_overlay(self):
        self.movie.stop()
        self.setVisible(False)


    def set_message(self, msg):
        self.message.setText(msg)


    def set_state_waiting(self):
        self.btn_retry.setVisible(False)
        self.btn_cancel.setVisible(True)


    def set_state_failed(self):
        self.btn_retry.setVisible(True)
        self.btn_cancel.setVisible(True)


    def set_state_success(self):
        self.btn_retry.setVisible(False)
        self.btn_cancel.setVisible(False)
