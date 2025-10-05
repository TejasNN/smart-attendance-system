from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from datetime import datetime, timedelta

class LogsWindow(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Attendance Logs")
        self.resize(600, 400)

        layout = QVBoxLayout()

        # Date filter dropdown
        self.date_filter = QComboBox()
        self.date_filter.addItems(["Today", "This Week", "This Month"])
        self.date_filter.currentIndexChanged.connect(self.load_logs)
        layout.addWidget(self.date_filter)

        # Table to display logs
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Employee ID", "Name", "Department","Date", "Status", "Timestamp"])
        layout.addWidget(self.table)

        # Static UI styling (apply once)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Apply custom header and table styling
        self.setup_table_style()

        # Button to refresh logs
        self.btn_refresh = QPushButton("Refresh Logs")
        self.btn_refresh.clicked.connect(self.load_logs)
        layout.addWidget(self.btn_refresh)

        self.setLayout(layout)

        # Load logs on initialization
        self.load_logs()

    
    def setup_table_style(self):
        """Enhances the visual styling of the table and headers."""
        header = self.table.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f0f0;
                color: #000000;
                font-weight: bold;
                border-bottom: 1px solid #a0a0a0;
                padding: 2px;
            }
        """)

        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                selection-background-color: #dfe6e9;
                selection-color: #2d3436;
            }
            QTableWidget::item {
                padding: 2px;
            }
        """)


    def load_logs(self):
        filter_option = self.date_filter.currentText()
        today = datetime.today()

        if filter_option == "Today":
            start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == "This Week":
            start_date = today - timedelta(days=today.weekday()) # Monday of this week
        elif filter_option == "This Month":
            start_date = today.replace(day=1)
        else:
            start_date = None

        query = {}
        if start_date:
            query["date"] = {"$gte": start_date.strftime("%Y-%m-%d")}

        logs = list(self.db.collection.find(query).sort("date", -1)) # Sort by the most recent

        self.table.setRowCount(len(logs))

        for row, log in enumerate(logs):
            self.table.setItem(row, 0, QTableWidgetItem(str(log.get("employee_id", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(log.get("name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(log.get("department", "")))
            self.table.setItem(row, 3, QTableWidgetItem(log.get("date", "")))
            self.table.setItem(row, 4, QTableWidgetItem(log.get("status", "")))
            self.table.setItem(row, 5, QTableWidgetItem(log.get("timestamp", "")))

            # dynamic formatting (row-specific)
            for col in range(6):
                item = self.table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Color coding for status
            status_item = self.table.item(row, 4)
            if status_item:
                status_text = status_item.text().lower()
                if "present" in status_text:
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    status_item.setForeground(Qt.GlobalColor.red)
