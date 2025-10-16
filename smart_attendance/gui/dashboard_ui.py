from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QComboBox, QDateEdit, QSizePolicy, QStackedWidget, 
    QGraphicsDropShadowEffect
)
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis
from PyQt6.QtCore import (
    Qt, QDate, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    QSize, QParallelAnimationGroup
)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter
import datetime

class DashboardUI(QWidget):
    date_filter_changed = pyqtSignal(str, object, object)

    def __init__(self, logged_user = "Admin", parent=None):
        super().__init__(parent)
        self.logged_user = logged_user
        self.sidebar_anim = None
        self.sidebar_anim2 = None
        self.sidebar_expanded = True
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
        
        self.btn_dashboard = make_sidebar_buttons("  Dashboard", "assets/icons/dashboard")
        self.btn_register = make_sidebar_buttons("  Register", "assets/icons/register")
        self.btn_attendance = make_sidebar_buttons("  Mark Attendance", "assets/icons/attendance")
        self.btn_logs = make_sidebar_buttons("  View Logs", "assets/icons/logs")
        self.btn_absentees = make_sidebar_buttons("  Mark Absentees", "assets/icons/absentees")

        for btn in (
            self.btn_dashboard, 
            self.btn_register, 
            self.btn_attendance, 
            self.btn_logs, 
            self.btn_absentees,
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
        title = QLabel("Attendance Dashboard")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        top_layout.addWidget(title)
        top_layout.addStretch()
        self.datetime_label = QLabel()
        # self.datetime_label = QLabel(datetime.datetime.now().strftime("%A, %d %B %Y  %H:%M:%S"))
        top_layout.addWidget(self.datetime_label)
        user_label = QLabel(f"|     Logged in: {self.logged_user}")
        top_layout.addWidget(user_label)
        right_container.addWidget(topbar)

        # Central rounded content area (this will be a QStackedWidget so we can swap content later)
        self.central_frame = QFrame()
        self.central_frame.setObjectName("centralFrame")
        central_layout = QVBoxLayout(self.central_frame)
        central_layout.setContentsMargins(16,16,16,16)
        central_layout.setSpacing(12)

        # Filter row (date filter + custom datepickers)
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_row.addWidget(QLabel("Date Range:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Today", "This Week", "This Month", "This Year", "Custom"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_change)
        filter_row.addWidget(self.filter_combo)

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate())
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        # hide custom pickers by default
        self.from_date.setVisible(False)
        self.to_date.setVisible(False)
        filter_row.addWidget(self.from_date)
        filter_row.addWidget(self.to_date)

        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("applyBtn")
        apply_btn.setFixedHeight(34)
        apply_btn.clicked.connect(self._emit_filter_change)
        filter_row.addWidget(apply_btn)
        filter_row.addStretch()

        central_layout.addLayout(filter_row)


        # Metrics grid: 3 cols x 2 rows (six metrics)
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(16)

        # create metric cards and store references to value QLabel for updates
        self.metric_labels = {}
        metric_names = [
            "Total Employees", "Present", "Absent",
            "Attendance Rate", "Today Late", "Avg Check-in Time"
        ]
        positions = [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)]
        for name, pos in zip(metric_names, positions):
            w = self._metric_card(name, "0")
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            metrics_grid.addWidget(w, pos[0], pos[1])
        central_layout.addLayout(metrics_grid)

        # Charts area (pie + bar horizontally)
        charts_row = QHBoxLayout()
        charts_row.setSpacing(12)

        # Pie chart
        self.pie_series = QPieSeries()
        self.pie_chart = QChart()
        self.pie_chart.addSeries(self.pie_series)
        self.pie_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.pie_view = QChartView(self.pie_chart)
        self.pie_view.setMinimumHeight(260)
        charts_row.addWidget(self.pie_view, 1)

        # # Bar chart
        self.bar_chart = QChart()
        self.bar_series = QBarSeries()
        self.bar_chart.addSeries(self.bar_series)
        self.bar_view = QChartView(self.bar_chart)
        self.bar_view.setMinimumHeight(260)
        charts_row.addWidget(self.bar_view, 2)

        self.pie_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.bar_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        central_layout.addLayout(charts_row)

        # Make the central content a stacked widget so other windows (register/attendance/logs) can be inserted here
        self.content_stack = QStackedWidget()
        self.content_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # page 0 = dashboard central_frame (we'll add central_frame into the stack)
        dashboard_page = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_page)
        dashboard_layout.setContentsMargins(0,0,0,0)
        dashboard_layout.addWidget(self.central_frame)
        self.content_stack.addWidget(dashboard_page)

        right_container.addWidget(self.content_stack)

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

        /* Metric Cards */
        QFrame#metricCard {
            background-color: #f9fafb;
            border-radius: 14px;
            border: 1px solid #e5e7eb;
        }

        /* Apply Button */
        QPushButton#applyBtn {
            background-color: #2563eb;
            color: #ffffff;
            border-radius: 8px;
            padding: 6px 12px;
        }

        QPushButton#applyBtn:hover {
            background-color: #1d4ed8;
        }
                           
        #centralFrame QMessageBox,
        #contentStack QMessageBox  {
            background-color: none; 
            background: none;
            border: none;
            border-radius: 0;
            color: black; 
        }
    """)


    def _start_clock(self):
        # update datetime label every second
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)


    def _update_clock(self):
        self.datetime_label.setText(datetime.datetime.now().strftime("%A, %d %B %Y  %H:%M:%S"))    


    # ---------------- metric card factory ----------------
    def _metric_card(self, title, value):
        box = QFrame()
        # NO internal borders; single entity: title and value stacked with spacing
        # box.setStyleSheet("""
        #     QFrame { background-color: #f6f8fa; border-radius: 10px; padding: 12px; }
        #     QLabel { color: #0f1720; }
        # """)
        box.setObjectName("metricCard")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setOffset(0,4)
        box.setGraphicsEffect(shadow)
        metric_card = QVBoxLayout(box)
        metric_card.setSpacing(8)
        label_title = QLabel(title)
        label_title.setFont(QFont("Arial", 10))
        label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_value = QLabel(value)
        label_value.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        label_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        metric_card.addWidget(label_title)
        metric_card.addWidget(label_value)
        # store reference for updates
        self.metric_labels[title] = label_value
        return box
    
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
            self.btn_dashboard,
            self.btn_register,
            self.btn_attendance,
            self.btn_logs,
            self.btn_absentees,
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
            texts = ["  Dashboard", "  Register", "  Mark Attendance", "  View Logs", "  Mark Absentees"]
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
    

    # ---------------- filter handling ----------------
    def _on_filter_change(self, text):
        is_custom = (text == "Custom")
        self.from_date.setVisible(is_custom)
        self.to_date.setVisible(is_custom)


    def _emit_filter_change(self):
        text = self.filter_combo.currentText()
        from_py = None
        to_py = None
        if text == "Custom":
            fd = self.from_date.date()
            td = self.to_date.date()
            from_py = datetime.date(fd.year(), fd.month(), fd.day())
            to_py = datetime.date(td.year(), td.month(), td.day())
        self.date_filter_changed.emit(text, from_py, to_py)


    # ---------------- Helpers to update UI from MainWindow ----------------
    def update_metrics(self, metrics_dict):
        """
        metrics_dict: mapping of metric title -> string value
        Example: {"Total Employees": "120", "Present": "100", ...}
        """
        for k, v in metrics_dict.items():
            lbl = self.metric_labels.get(k)
            if lbl:
                lbl.setText(str(v))


    def update_pie(self, present, absent):
        try:
            self.pie_series.clear()
            self.pie_series.append("Present", present)
            self.pie_series.append("Absent", absent)
            self.pie_chart.setTitle("Present vs Absent")
        except Exception as e:
            print("pie update error:", e)


    def update_bar(self, categories, values):
        try:
            # rebuild bar series
            self.bar_chart.removeAllSeries()
            set0 = QBarSet("Present")
            set0.append(values)
            series = QBarSeries()
            series.append(set0)
            self.bar_chart.addSeries(series)

            axisX = QBarCategoryAxis()
            axisX.append(categories)
            # remove existing axes, attach new
            for ax in self.bar_chart.axes():
                self.bar_chart.removeAxis(ax)
            self.bar_chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axisX)
            self.bar_chart.setTitle("Daily Present Counts")
        except Exception as e:
            print("bar update error:", e)


    def highlight_active_button(self, active_button):
        for btn in [self.btn_dashboard, self.btn_register, self.btn_attendance, self.btn_logs, self.btn_absentees]:
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
