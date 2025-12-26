from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy, QStackedWidget, QToolButton
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, 
    QSize, pyqtSignal
)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter
from desktop_app.gui.widgets.overlay import ProvisioningOverlay
from desktop_app.gui.widgets.login_overlay import LoginOverlay
from desktop_app.gui.widgets.vision_toast import VisionToast
import datetime, os

base_path = os.path.dirname(os.path.abspath(__file__))

class DashboardUI(QWidget):
    login_submitted = pyqtSignal(str, str)
    login_cancel_requested = pyqtSignal()
    forgot_password_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sidebar_anim = None
        self.sidebar_expanded = True
        self._loader_retry_callback = None
        self._loader_cancel_callback = None
        self._build_ui()
        self._start_clock()


    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12,12,12,12)
        outer.setSpacing(12)
        
        # ----------------------------------
        # Sidebar
        # ----------------------------------
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebarFrame")

        self.sidebar_expanded = True
        self.sidebar_width_expanded = 220
        self.sidebar_width_collapsed = 80

        self.sidebar_frame.setMinimumWidth(self.sidebar_width_collapsed)
        self.sidebar_frame.setMaximumWidth(self.sidebar_width_expanded)
        self.sidebar_frame.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding
        )

        sb_layout = QVBoxLayout(self.sidebar_frame)
        sb_layout.setContentsMargins(10, 10, 10, 10)
        sb_layout.setSpacing(18)

        # ---------- Toggle Button ----------
        self.btn_toggle = QToolButton()
        self.btn_toggle.setIcon(self._get_white_icon(
            os.path.join(base_path, "..", "assets", "icons", "menu.png")
        ))
        self.btn_toggle.setIconSize(QSize(24, 24))
        self.btn_toggle.setAutoRaise(False)
        self.btn_toggle.setObjectName("sidebarBtn")
        self.btn_toggle.setMinimumHeight(42)
        self.btn_toggle.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        self.btn_toggle.clicked.connect(self.toggle_sidebar)

        sb_layout.addWidget(self.btn_toggle)

        sb_layout.addSpacing(10)

        # ---------- Sidebar Buttons Factory ----------
        def make_sidebar_button(text, icon_path):
            btn = QToolButton()
            btn.setText(text)
            btn.setIcon(self._get_white_icon(icon_path))
            btn.setIconSize(QSize(22, 22))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(42)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setObjectName("sidebarBtn")
            return btn

        attendance_icon = os.path.join(base_path, "..", "assets", "icons", "attendance.png")
        logs_icon = os.path.join(base_path, "..", "assets", "icons", "logs.png")

        self.btn_attendance = make_sidebar_button("  Mark Attendance", attendance_icon)
        self.btn_logs = make_sidebar_button("  View Logs", logs_icon)

        sb_layout.addWidget(self.btn_attendance)
        sb_layout.addWidget(self.btn_logs)
        sb_layout.addStretch()


        # Right: Combine topbar + central rounded content into a single visual unit
        self.right_panel = QWidget()
        right_container = QVBoxLayout(self.right_panel)
        right_container.setSpacing(10)
        right_container.setContentsMargins(0,0,0,0)
        self.right_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # Topbar (styled, single entity visually connection tot sidebar)
        topbar = QFrame()
        topbar.setObjectName("topbar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(14, 8, 14, 8)
        title = QLabel("Attendance")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        top_layout.addWidget(title)
        top_layout.addStretch()
        self.datetime_label = QLabel()
        # self.datetime_label = QLabel(datetime.datetime.now().strftime("%A, %d %B %Y  %H:%M:%S"))
        top_layout.addWidget(self.datetime_label)
        right_container.addWidget(topbar)

        # Central rounded content area (this will be a QStackedWidget so we can swap content later)
        self.central_frame = QFrame()
        self.central_frame.setObjectName("centralFrame")
        central_layout = QVBoxLayout(self.central_frame)
        central_layout.setContentsMargins(16,16,16,16)
        central_layout.setSpacing(12)

        # Make the central content a stacked widget so other windows (attendance/logs) can be inserted here
        self.content_stack = QStackedWidget()
        self.content_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        self.content_stack.setContentsMargins(0,0,0,0)
        self.central_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # page 0 = dashboard central_frame (we'll add central_frame into the stack)
        dashboard_page = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_page)
        dashboard_layout.setContentsMargins(0,0,0,0)
        dashboard_layout.addWidget(self.central_frame)
        self.content_stack.addWidget(dashboard_page)

        right_container.addWidget(self.content_stack)

        # ---------- Overlay Layer ----------
        self.overlay_layer = QFrame(self)
        self.overlay_layer.setStyleSheet("background: transparent;")
        self.overlay_layer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.overlay_layer.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.overlay_layer.setGeometry(self.rect())
        self.overlay_layer.show()
        self.overlay_layer.raise_()

        overlay_layout = QVBoxLayout(self.overlay_layer)
        overlay_layout.setContentsMargins(0,0,0,0)
        overlay_layout.setSpacing(0)

        self.provision_overlay = ProvisioningOverlay(self.overlay_layer)
        self.login_overlay = LoginOverlay(self.overlay_layer)

        overlay_layout.addWidget(self.provision_overlay)
        overlay_layout.addWidget(self.login_overlay)

        self.provision_overlay.hide()
        self.login_overlay.hide()

        # login submitted → bubble upward via signal
        self.login_overlay.login_requested.connect(
            lambda username, password: self.login_submitted.emit(username, password)
        )

        # cancel login -> bubble upward
        self.login_overlay.cancel_requested.connect(
            lambda: self.login_cancel_requested.emit())
        
        # forgot password
        self.login_overlay.forgot_password_requested.connect(
            lambda: self.forgot_password_requested.emit()
        )

        # Add sidebar and right_container to outer layout with proper stretch ratio
        outer.addWidget(self.sidebar_frame, 0)
        outer.addWidget(self.right_panel, 1)

        # set the layout on this wiget so children show
        self.setLayout(outer)

        self.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI';
            font-size: 12pt;
            color: #e5e7eb; /* default for dark areas like sidebar & topbar */
            background-color: #f4f6f9;
        }

        /* Sidebar */
        #sidebarFrame {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #1f2937, stop:1 #111827);
            border-radius: 16px;
            padding: 8px;
        }
            
        #btnToggle {
            border: none;
            background: transparent;
            padding: 0;
        }
        #btnToggle:hover {
            background-color: rgba(255,255,255,0.1);
        }

        QToolButton#sidebarBtn {
            background: transparent;
            color: #d1d5db;
            border-radius: 10px;
            padding: 6px 10px;
            font-weight: 500;
        }

        QToolButton#sidebarBtn:hover {
            background-color: rgba(255,255,255,0.12);
            color: white;
        }

        QToolButton#sidebarBtn:pressed {
            background-color: rgba(255,255,255,0.2);
        }

        QToolButton#sidebarBtn[active="true"] {
            background-color: #2563eb;
            color: white;
        }
                           
        QToolButton:focus, 
        QPushButton:focus {
            outline: 0;
            border: none;
        }

        /* Topbar (Dark) */
        #topbar {
            background-color: #111827;
            border-radius: 10px;
            padding: 10px 16px;
            color: #e5e7eb;
            border: 1px solid #1f2937;
        }

        #topbar QLabel {
            background-color: transparent;
            color: #e5e7eb;
            font-weight: 500;
        }

        /* === Central Light Theme (applies to all pages in the stack) === */
        #centralFrame, 
        #contentStack, 
        #contentStack QWidget {
            background-color: #ffffff;
            border-radius: 10px;
            border: 1px solid #e5e7eb;
            color: #111827;
        }

        #centralFrame QLabel,
        #contentStack QLabel {
            color: #1f2937;  /* dark gray-blue */
        }

        #centralFrame QPushButton,
        #contentStack QPushButton {
            color: #111827;
            background-color: #f3f4f6;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 6px 12px;
        }

        #centralFrame QPushButton:hover,
        #contentStack QPushButton:hover {
            background-color: #e5e7eb;
        }

        #centralFrame QComboBox, 
        #contentStack QComboBox, 
        #centralFrame QDateEdit,
        #contentStack QDateEdit {
            background-color: #ffffff;
            border: 1px solid #d1d5db;
            padding: 4px 8px;
            color: #111827;
        }

        #centralFrame QComboBox QAbstractItemView,
        #contentStack QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #111827;
            selection-background-color: #2563eb;
            selection-color: #ffffff;
        }
    """)


    def _start_clock(self):
        # update datetime label every second
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)


    def _update_clock(self):
        self.datetime_label.setText(datetime.datetime.now().strftime("%A, %d %B %Y  %H:%M:%S"))    
    
    # ---------------- Sidebar animation ----------------
    def toggle_sidebar(self):
        start = self.sidebar_frame.width()

        if self.sidebar_expanded:
            end = self.sidebar_width_collapsed
        else:
            end = self.sidebar_width_expanded

        # animate max
        anim_max = QPropertyAnimation(self.sidebar_frame, b"maximumWidth")
        anim_max.setDuration(300)
        anim_max.setStartValue(start)
        anim_max.setEndValue(end)
        anim_max.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # animate min as well (smooth + stable)
        anim_min = QPropertyAnimation(self.sidebar_frame, b"minimumWidth")
        anim_min.setDuration(300)
        anim_min.setStartValue(start)
        anim_min.setEndValue(end)
        anim_min.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # run both
        anim_max.start()
        anim_min.start()

        self.sidebar_anim = anim_max
        self.sidebar_anim2 = anim_min

        def after():
            if self.sidebar_expanded:
                # finished collapsing
                for btn in (self.btn_attendance, self.btn_logs):
                    btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    btn.setStyleSheet("""
                        QToolButton {
                            padding:0px; 
                            margin: 0px;
                            qproperty-iconSize: 24px;
                        }
                    """)
            else:
                # finished expanding
                for btn in (self.btn_attendance, self.btn_logs):
                    btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)                    
                    btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                    btn.setStyleSheet("""
                        QToolButton {
                            padding-left: 10px;
                            qproperty-iconSize: 24px;
                        }
                    """)
            self.sidebar_expanded = not self.sidebar_expanded

        anim_max.finished.connect(after)


    def highlight_active_button(self, active_button):
        for btn in [self.btn_attendance, self.btn_logs]:
            btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        active_button.setProperty("active", True)
        active_button.style().unpolish(active_button)
        active_button.style().polish(active_button)

    def _get_white_icon(self, path, size=22):
        """Load an icon and tint it white for dark backgrounds."""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                size, 
                size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            tinted = QPixmap(pixmap.size())
            tinted.fill(Qt.GlobalColor.transparent)
            painter = QPainter(tinted)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(tinted.rect(), Qt.GlobalColor.white)
            painter.end()
            return QIcon(tinted)
        return QIcon(path)
    

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Keep overlay layer full size
        if self.overlay_layer:
            self.overlay_layer.setGeometry(self.rect())

    
    def show_waiting_controls(self, show=True):
        self.provision_overlay.btn_retry.setVisible(show)
        self.provision_overlay.btn_cancel.setVisible(show)


    def show_loader(self, message="Working..."):
        self.force_sidebar_visible()
        self.provision_overlay.set_message(message)
        self.overlay_layer.show()
        self.overlay_layer.raise_()
        self.provision_overlay.show_overlay()

    def update_loader(self, msg):
        self.provision_overlay.set_message(msg)

    def hide_loader(self):
        self.provision_overlay.hide_overlay()

    def show_overlay_feedback(self, msg, msg_type="info"):
        VisionToast(self, msg, msg_type)

    def show_login_overlay(self):
        self.force_sidebar_visible()
        self.login_overlay.show()
        self.overlay_layer.show()
        self.overlay_layer.raise_()
        self.login_overlay.show_overlay()

    def _hide_login_overlay(self):
        self.login_overlay.hide_overlay()
        self.overlay_layer.hide()
        self.force_sidebar_visible()

    def force_sidebar_visible(self):
        self.btn_attendance.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_logs.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
