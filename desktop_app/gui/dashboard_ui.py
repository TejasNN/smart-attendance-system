from collections import deque
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QSizePolicy, QStackedWidget, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, 
    QSize
)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QMovie
import datetime

class DashboardUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sidebar_anim = None
        self.sidebar_anim2 = None
        self.sidebar_expanded = True
        self._loader_retry_callback = None
        self._loader_cancel_callback = None
        self._build_ui()
        self._start_clock()

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12,12,12,12)
        outer.setSpacing(12)
        
        # Left: Sidebar (rounded)
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebarFrame")
        self.sidebar_frame.setFixedWidth(220)
        self.sidebar_frame.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        sb_layout = QVBoxLayout(self.sidebar_frame)
        sb_layout.setContentsMargins(12,12,12,12)
        sb_layout.setSpacing(12)

        # Toggle button at top left
        self.btn_toggle = QPushButton()
        self.btn_toggle.setObjectName("btnToggle")
        icon_path = "assets/icons/menu.png"
        self.btn_toggle.setIcon(QIcon(self._get_white_icon(icon_path)))
        self.btn_toggle.setIconSize(QSize(24,24))
        self.btn_toggle.setFixedSize(38,38)
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.1);
                border-radius: 6px;
            }
        """)

        self.toggle_container = QHBoxLayout()
        self.toggle_container.addWidget(self.btn_toggle, alignment=Qt.AlignmentFlag.AlignRight)
        sb_layout.addLayout(self.toggle_container)

        sb_layout.addSpacing(22)    # add 22px vertical gap between menu and other sidebar buttons

        # Sidebar buttons with icons
        def make_sidebar_buttons(text, icon_path):
            btn = QPushButton(text)
            btn.setIcon(self._get_white_icon(icon_path))
            btn.setIconSize(QSize(24,24))
            btn.setMinimumHeight(40)
            btn.setStyleSheet("text-align: left; padding-left: 10px;")
            return btn
        
        self.btn_attendance = make_sidebar_buttons("  Mark Attendance", "assets/icons/attendance")
        self.btn_logs = make_sidebar_buttons("  View Logs", "assets/icons/logs")

        for btn in ( 
            self.btn_attendance, 
            self.btn_logs
        ):
            btn.setMinimumHeight(40)
            btn.setStyleSheet("text-align: left; padding-left: 10px;")
            sb_layout.addWidget(btn)
        sb_layout.addStretch()

        # Right: Combine topbar + central rounded content into a single visual unit
        right_container = QVBoxLayout()
        right_container.setSpacing(10)
        right_container.setContentsMargins(0,0,0,0)


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
        self.content_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # page 0 = dashboard central_frame (we'll add central_frame into the stack)
        dashboard_page = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_page)
        dashboard_layout.setContentsMargins(0,0,0,0)
        dashboard_layout.addWidget(self.central_frame)
        self.content_stack.addWidget(dashboard_page)

        right_container.addWidget(self.content_stack)

        # -------------------------------
        # Loader overlay that covers entire DashboardUI (not just content)
        # -------------------------------
        self._loader_overlay = QFrame(self.window())
        self._loader_overlay.setVisible(False)
        self._loader_overlay.setObjectName("loaderOverlay")
        self._loader_overlay.setStyleSheet("""
            #loaderOverlay {
                background-color: rgba(255, 255, 255, 210);
            }
        """)

        loader_layout = QVBoxLayout(self._loader_overlay)
        loader_layout.setContentsMargins(24, 24, 24, 24)
        loader_layout.setSpacing(16)
        loader_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Loader spinner (centered)
        self._loader_spinner = QLabel()
        spinner_path = "assets/icons/loader.gif"
        try:
            self._loader_movie = QMovie(spinner_path)
            self._loader_spinner.setMovie(self._loader_movie)
        except Exception:
            self._loader_spinner.setText("Loading...")
            self._loader_movie = None
        self._loader_spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Message label (below spinner)
        self._loader_message = QLabel("Working...")
        self._loader_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loader_message.setWordWrap(True)
        self._loader_message.setStyleSheet("""
            color: black;
            font-size: 16px;
            font-weight: 600;
            padding: 10px 20px;
        """)
        self._loader_message.setMinimumWidth(380)
        self._loader_message.setMaximumWidth(700)

        self._loader_message_effect = QGraphicsOpacityEffect()
        self._loader_message.setGraphicsEffect(self._loader_message_effect)
        self._loader_message_effect.setOpacity(1.0)

        self._loader_message_queue = deque()
        self._loader_message_timer = QTimer()
        self._loader_message_timer.timeout.connect(self._show_next_loader_message)
        self._loader_message_timer.setSingleShot(True)
        self._current_loader_animating = False

        # Add to layout
        loader_layout.addWidget(self._loader_spinner)
        loader_layout.addWidget(self._loader_message)

        # Retry + Cancel controls (below message)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._loader_retry_btn = QPushButton("Retry")
        self._loader_retry_btn.setFixedHeight(34)
        self._loader_retry_btn.setMinimumWidth(120)
        self._loader_retry_btn.setStyleSheet("color: black;")
        self._loader_retry_btn.clicked.connect(lambda: self._on_loader_retry())

        self._loader_cancel_btn = QPushButton("Cancel")
        self._loader_cancel_btn.setFixedHeight(34)
        self._loader_cancel_btn.setMinimumWidth(120)
        self._loader_cancel_btn.setStyleSheet("color: black;")
        self._loader_cancel_btn.clicked.connect(lambda: self._on_loader_cancel())

        btn_row.addStretch()
        btn_row.addWidget(self._loader_retry_btn)
        btn_row.addWidget(self._loader_cancel_btn)
        btn_row.addStretch()

        loader_layout.addLayout(btn_row)

        # Initially hide controls — only show when waiting for credential
        self._loader_retry_btn.setVisible(False)
        self._loader_cancel_btn.setVisible(False)

        # Add sidebar and right_container to outer layout with proper stretch ratio
        outer.addWidget(self.sidebar_frame, 0)
        outer.addLayout(right_container, 1)

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

        #sidebarFrame QPushButton {
            background-color: transparent;
            color: #d1d5db;
            border: none;
            border-radius: 8px;
            padding: 10px;
            text-align: left;
            font-weight: 500;
        }

        #sidebarFrame QPushButton:hover {
            background-color: rgba(255,255,255,0.1);
            color: #ffffff;
        }

        #sidebarFrame QPushButton:pressed {
            background-color: rgba(255,255,255,0.2);
        }

        #sidebarFrame QPushButton[active="true"] {
            background-color: #2563eb;
            color: #ffffff;
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
        # toggle between 220 and 60 px; keep animation instance on self
        start = self.sidebar_frame.width()
        end = 80 if self.sidebar_expanded else 220

        self.sidebar_anim = QPropertyAnimation(self.sidebar_frame, b"maximumWidth", self)
        self.sidebar_anim.setDuration(300)
        self.sidebar_anim.setStartValue(start)
        self.sidebar_anim.setEndValue(end)
        self.sidebar_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # also animate minimumWidth for smoother effect
        self.sidebar_anim2 = QPropertyAnimation(self.sidebar_frame, b"minimumWidth", self)
        self.sidebar_anim2.setDuration(300)
        self.sidebar_anim2.setStartValue(start)
        self.sidebar_anim2.setEndValue(end)
        self.sidebar_anim2.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # start both animations
        self.sidebar_anim.start()
        self.sidebar_anim2.start()

        # After animation finishes, update sidebar button labels and toggle button alignment
        def after_animation():
            self._update_sidebar_labels()
            # Toggle button alignment: left-aligned when expanded, centered when collapsed
            if self.sidebar_expanded:
                self.toggle_container.setAlignment(self.btn_toggle, Qt.AlignmentFlag.AlignRight)
            else:
                self.toggle_container.setAlignment(self.btn_toggle, Qt.AlignmentFlag.AlignHCenter)

        # update labels after animation
        self.sidebar_anim2.finished.connect(after_animation)

        # Flip the sidebar state
        self.sidebar_expanded = not self.sidebar_expanded


    def _update_sidebar_labels(self):
        """Update sidebar button labels and icon alignment based on collapse state."""
        # Sidebar buttons
        sidebar_buttons = (
            self.btn_attendance,
            self.btn_logs
        )

        if not self.sidebar_expanded:
            # Collapsed: show only icons, center them
            for btn in sidebar_buttons:
                btn.setText("")
                btn.setStyleSheet("""
                    QPushButton {
                        qproperty-iconSize: 22px;
                        text-align: center;
                        padding: 0px;
                        margin: 0px;
                    }
                """)
        else:
            # Expanded: restore text and left alignment
            texts = ["  Mark Attendance", "  View Logs"]
            for btn, text in zip(sidebar_buttons, texts):
                btn.setText(text)
                btn.setStyleSheet("""
                    QPushButton {
                        qproperty-iconSize: 22px;
                        text-align: left;
                        padding-left: 10px;
                        margin: 0px;
                    }
                """)


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
            pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            tinted = QPixmap(pixmap.size())
            tinted.fill(Qt.GlobalColor.transparent)
            painter = QPainter(tinted)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(tinted.rect(), Qt.GlobalColor.white)
            painter.end()
            return QIcon(tinted)
        return QIcon(path)

    
    # def animate_page_transition(self, old_index, new_index, direction="left"):
    #     """
    #     Animate smooth slide transition between two pages in the content stack.
    #     direction: 'left' (default) or 'right'
    #     """
    #     old_widget = self.content_stack.widget(old_index)
    #     new_widget = self.content_stack.widget(new_index)

    #     if not old_widget or not new_widget:
    #         # fallback to normal change if invalid
    #         self.content_stack.setCurrentIndex(new_index)
    #         return
        
    #     stack_geometry = self.content_stack.geometry()
    #     width = stack_geometry.width()
    #     height = stack_geometry.height()

    #     # Starting position for animation
    #     if direction == "left":
    #         new_start = QRect(width, 0, width, height)
    #         new_end = QRect(0, 0, width, height)
    #         old_end = QRect(-width, 0, width, height)
    #     else:
    #         new_start = QRect(-width, 0, width, height)
    #         new_end = QRect(0, 0, width, height)
    #         old_end = QRect(width, 0, width, height)

    #     # Prepare new widget
    #     new_widget.setGeometry(new_start)
    #     new_widget.show()

    #     # Animation for old and new pages
    #     anim_old = QPropertyAnimation(old_widget, b"geometry")
    #     anim_old.setDuration(400)
    #     anim_old.setStartValue(stack_geometry)
    #     anim_old.setEndValue(old_end)
    #     anim_old.setEasingCurve(QEasingCurve.Type.InOutCubic)

    #     anim_new = QPropertyAnimation(new_widget, b"geometry")
    #     anim_new.setDuration(400)
    #     anim_new.setStartValue(new_start)
    #     anim_new.setEndValue(new_end)
    #     anim_new.setEasingCurve(QEasingCurve.Type.InOutCubic)

    #     # Group animations together
    #     group = QParallelAnimationGroup()
    #     group.addAnimation(anim_old)
    #     group.addAnimation(anim_new)

    #     def on_finished():
    #         self.content_stack.setCurrentIndex(new_index)
    #         new_widget.setGeometry(0, 0, width, height)
    #         old_widget.setGeometry

    #     group.finished.connect(on_finished)
    #     group.start()
    #     self._page_transition_anim = group


    # ------- Loader overlay controls helper functions --------

    def show_loader(self, initial_message: str = "Working..."):
        # ensure overlay covers entire main window
        w = self.window()
        self._loader_overlay.setGeometry(0,0, w.width(), w.height())
        if self._loader_movie:
            try:
                self._loader_movie.start()
            except Exception:
                raise

        self._loader_message.setText(initial_message)
        self._loader_message_queue.clear()
        self._loader_overlay.raise_()
        self._loader_overlay.setWindowOpacity(0)
        self._loader_overlay.setVisible(True)

        # Fade-in animation
        self._fade_in = QPropertyAnimation(self._loader_overlay, b"windowOpacity")
        self._fade_in.setDuration(300)
        self._fade_in.setStartValue(0)
        self._fade_in.setEndValue(1)
        self._fade_in.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade_in.start()


    def update_loader(self, message: str):
        self._loader_message_queue.append(message)
        if not self._current_loader_animating:
            self._show_next_loader_message()

    
    def hide_loader(self):
        if self._loader_movie:
            try:
                self._loader_movie.stop()
            except Exception:
                raise

        # Fade-out animation
        self._fade_out = QPropertyAnimation(self._loader_overlay, b"windowOpacity")
        self._fade_out.setDuration(300)
        self._fade_out.setStartValue(1)
        self._fade_out.setEndValue(0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade_out.finished.connect(lambda: self._loader_overlay.setVisible(False))
        self._fade_out.start()


    def _show_next_loader_message(self):
        if not self._loader_message_queue:
            self._current_loader_animating = False

            # --- Smooth fade-out for the final loader overlay ---
            fade_out_final = QPropertyAnimation(self._loader_overlay, b"windowOpacity")
            fade_out_final.setDuration(400)
            fade_out_final.setStartValue(1)
            fade_out_final.setEndValue(0)
            fade_out_final.setEasingCurve(QEasingCurve.Type.InOutCubic)
            fade_out_final.finished.connect(lambda: self._loader_overlay.setVisible(False))
            fade_out_final.start()

            # Prevent garbage collection
            self._fade_out_final = fade_out_final
            return

        self._current_loader_animating = True
        next_message = self._loader_message_queue.popleft()

        if not hasattr(self, "_loader_message_effect"):
            # fallback to simple update if effect missing
            self._loader_message.setText(next_message)
            self._loader_message.repaint()
        else:
            # Step 1: Fade out current text
            fade_out = QPropertyAnimation(self._loader_message_effect, b"opacity")
            fade_out.setDuration(180)
            fade_out.setStartValue(1)
            fade_out.setEndValue(0)
            fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
            fade_out.finished.connect(lambda: self._fade_in_message(next_message))
            fade_out.start()

            # Prevent garbage collection
            self._fade_out_message = fade_out

        # Slightly longer delay for the final message
        delay = 900 if len(self._loader_message_queue) == 0 else 450
        self._loader_message_timer.start(delay)


    def _fade_in_message(self, text):
        self._loader_message.setText(text)
        fade_in = QPropertyAnimation(self._loader_message_effect, b"opacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)
        fade_in.start()
        self._fade_in_message_anim = fade_in

    # controls for retry/cancel
    def show_waiting_controls(self, show: bool = True):
        """Show/hide retry & cancel buttons on overlay."""
        self._loader_retry_btn.setVisible(show)
        self._loader_cancel_btn.setVisible(show)

    
    def _on_loader_retry(self):
        if callable(self._loader_retry_callback):
            self._loader_retry_callback()

    
    def _on_loader_cancel(self):
        if callable(self._loader_cancel_callback):
            self._loader_cancel_callback()


    def set_loader_retry_callback(self, callback):
        self._loader_retry_callback = callback


    def set_loader_cancel_callback(self, callback):
        self._loader_cancel_callback = callback

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._loader_overlay.isVisible():
            w = self.window()
            self._loader_overlay.setGeometry(0, 0, w.width(), w.height())