# smart_attendance/gui/widgets/login_overlay.py
from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QLineEdit, QPushButton,
    QHBoxLayout, QFrame, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import ( 
    Qt, pyqtSignal, QPoint, QEasingCurve, QPropertyAnimation,
    QTimer
)
from PyQt6.QtGui import QPixmap, QFont
import os


class LoginOverlay(QFrame):
    cancel_requested = pyqtSignal()
    login_requested = pyqtSignal(str, str)          
    forgot_password_requested = pyqtSignal()        

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay, True)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setObjectName("loginOverlay")
        self.setVisible(False)

        self.setStyleSheet("""
        #loginOverlay {
            background: rgba(255,255,255,200);
        }

        #glassCard {
            background: rgba(255,255,255,180);
            border-radius: 18px;
            border: 1px solid rgba(200,200,200,180);
        }
                           
        #glassCard QLabel {
            color: #111827;
        }

        QLineEdit {
            background: rgba(255,255,255,120);
            border: 1px solid rgba(180,180,180,120);
            border-radius: 6px;
            padding: 8px;
            font-size: 14px;
            color: #111827;
        }

        QLineEdit:focus {
            border: 2px solid #4f46e5;
        }
                           
        QLineEdit::placeholder {
            color: #6b7280;
        }
                           
        QLineEdit[error="true"] {
            border: 2px solid #ef4444;
            background: rgba(255,200,200,140);
        }
                           
        QLineEdit[success="true"] {
            border: 2px solid #16a34a;
            background: rgba(180,255,200,110);
        }
                           
        QCheckBox {
            color: #111827;
        }

        QPushButton {
            padding: 8px 14px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
        }

        QPushButton#loginBtn {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #4f46e5, stop:1 #2563eb
            );
        }

        QPushButton#loginBtn:hover {
            background: #4338ca;
        }

        QPushButton#cancelBtn {
            background:#ef4444;
        }
                           
        QPushButton#cancelBtn:hover {
            background:#dc2626;
        }

        QLabel#forgotLabel {
            color:#2563eb;
            font-size:13px;
        }

        QLabel#forgotLabel:hover {
            text-decoration: underline;
        }
        """)

        base_path = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_path, "assets", "icons", "logo.png")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Glass card container
        self.card = QFrame()
        self.card.setObjectName("glassCard")
        self.card.setMinimumWidth(420)
        self.card.setMaximumWidth(1200)
        self.card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(12)
        card_layout.setStretch(0, 0)  # logo
        card_layout.setStretch(1, 0)  # title
        card_layout.setStretch(2, 1)  # username
        card_layout.setStretch(3, 1)  # password
        card_layout.setStretch(4, 0)  # remember
        card_layout.setStretch(5, 0)  # buttons
        card_layout.setStretch(6, 0)  # forgot


        # -------- Logo --------
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(pix)
        else:
            logo.setText("SMART ATTENDANCE")
            logo.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))

        # -------- Title --------
        title = QLabel("Operator Login")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))


        # -------- Inputs --------
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setMinimumHeight(38)
        self.username.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(38)
        self.password.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Remember Me
        self.remember = QCheckBox("Remember Me")

        # -------- Buttons --------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_login = QPushButton("Login")
        self.btn_login.setObjectName("loginBtn")
        self.btn_login.setMinimumHeight(38)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setMinimumHeight(38)

        btn_row.addWidget(self.btn_login)
        btn_row.addWidget(self.btn_cancel)

        # -------- Forgot Password --------
        self.forgot = QLabel("Forgot Password?")
        self.forgot.setObjectName("forgotLabel")
        self.forgot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.forgot.setCursor(Qt.CursorShape.PointingHandCursor)

        # -------- Assemble --------
        card_layout.addWidget(logo)
        card_layout.addWidget(title)
        card_layout.addWidget(self.username)
        card_layout.addWidget(self.password)
        card_layout.addWidget(self.remember)
        card_layout.addLayout(btn_row)
        card_layout.addWidget(self.forgot)

        layout.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignCenter)

        # -------- Events --------
        self.btn_cancel.clicked.connect(lambda: self.cancel_requested.emit())
        self.btn_login.clicked.connect(lambda: self._emit_login())
        self.forgot.mousePressEvent = lambda e: self.forgot_password_requested.emit()


    def _emit_login(self):
        username = self.username.text().strip()
        password = self.password.text().strip()

        has_error = False

        if not username:
            self.username.setProperty("error", True)
            self.username.setText("")
            self.username.style().unpolish(self.username)
            self.username.style().polish(self.username)
            has_error = True
        else:
            self.username.setProperty("error", False)

        if not password:
            self.password.setProperty("error", True)
            self.password.setText("")
            self.password.style().unpolish(self.password)
            self.password.style().polish(self.password)
            has_error = True
        else:
            self.password.setProperty("error", False)

        if has_error:
            self._shake_card()
            QTimer.singleShot(400, self._reset_error_visuals)
            return

        self.login_requested.emit(username, password)


    def _shake_card(self):
        if hasattr(self, "_shake_anim") and self._shake_anim is not None:
            self._shake_anim.stop()

        self._shake_anim = QPropertyAnimation(self.card, b"pos")
        self._shake_anim.setDuration(400)
        self._shake_anim.setKeyValueAt(0, self.card.pos())
        self._shake_anim.setKeyValueAt(0.25, self.card.pos() + QPoint(-12, 0))
        self._shake_anim.setKeyValueAt(0.50, self.card.pos() + QPoint(12, 0))
        self._shake_anim.setKeyValueAt(1, self.card.pos())
        self._shake_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._shake_anim.start()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        x = (self.width() - self.card.width()) // 2
        y = (self.height() - self.card.height()) // 2
        self.card.move(max(0,x), max(0,y))


    def show_overlay(self):
        parent = self.parentWidget()
        if parent:
            self.setGeometry(parent.rect())
            
        self.show()
        self.setVisible(True)
        self.raise_()
        self.setFocus()


    def hide_overlay(self):
        self.setVisible(False)
            
    
    def show_field_error_state(self, msg="Invalid credentials"):
        # turn both fields red
        for field in (self.username, self.password):
            field.setText("")
            field.setProperty("error", True)
            field.style().unpolish(field)
            field.style().polish(field)

        self._shake_card()

    
    def show_success_state(self):
        for field in (self.username, self.password):
            field.setProperty("success", True)
            field.style().unpolish(field)
            field.style().polish(field)
            QTimer.singleShot(1500, self._clear_success_state)

    
    def _clear_success_state(self):
        for field in (self.username, self.password):
            field.setProperty("success", False)
            field.style().unpolish(field)
            field.style().polish(field)

    
    def _reset_error_visuals(self):
        for field in (self.username, self.password):
            field.setProperty("error", False)
            field.style().unpolish(field)
            field.style().polish(field)
