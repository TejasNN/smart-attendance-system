from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
    QLineEdit, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from datetime import datetime, timedelta

class LogsWindow(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Attendance Logs")
        self.resize(800, 500)

        self.all_logs = []          # store all logs fetched from MongoDB
        self.filtered_logs = []     # store filtered logs based on search/filter

        main_layout = QVBoxLayout()

        # toop control bar layout
        top_layout = QHBoxLayout()

        # Date filter dropdown
        self.date_filter = QComboBox()
        self.date_filter.addItems(["Today", "This Week", "This Month"])
        self.date_filter.currentIndexChanged.connect(self.load_logs)
        top_layout.addWidget(self.date_filter)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search logs")
        self.search_box.textChanged.connect(self.apply_filters)
        top_layout.addWidget(self.search_box)

        # Reset Filter button
        self.btn_reset_filter = QPushButton("Reset filters")
        self.btn_reset_filter.clicked.connect(self.reset_filters)
        top_layout.addWidget(self.btn_reset_filter)

        # Add top_layout into main layout
        main_layout.addLayout(top_layout)

        # Table to display logs
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Employee ID", "Name", "Department","Date", "Status", "Timestamp"])

        # Static UI styling (apply once)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        main_layout.addWidget(self.table)

        # Apply custom header and table styling
        self.setup_table_style()

        # Button to refresh logs
        self.btn_refresh = QPushButton("Refresh Logs")
        self.btn_refresh.clicked.connect(self.load_logs)
        main_layout.addWidget(self.btn_refresh)

        self.setLayout(main_layout)

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

        self.all_logs = list(self.db.collection.find(query).sort("date", -1)) # Sort by the most recent
        self.apply_filters()    # show filtered (or all logs)

    def apply_filters(self):
        """Apply search-based filtering to logs"""
        search_text = self.search_box.text().lower()
        if not search_text:
            self.filtered_logs = self.all_logs
        else:
            self.filtered_logs = [
                log for log in self.all_logs
                if any(search_text in str(value).lower() for value in log.values())
            ]
        self.update_table()

    def reset_filters(self):
        """Reset search box, date filter, and reload all logs."""
        self.btn_reset_filter.setEnabled(False)
        self.search_box.clear()
        self.date_filter.setCurrentIndex(0)
        self.load_logs()
        self.btn_reset_filter.setEnabled(True)
    
    def add_table_item(self, row, col, text):
        """Helper to create a centered, styled table item."""
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        if col == 4:
            status_text = str(text).lower()
            if "present" in status_text:
                item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                item.setForeground(Qt.GlobalColor.red)

        return item

    def update_table(self):
        """Update QTableWidget with current filtered logs."""

        self.table.setSortingEnabled(False) # Temporarily disable sorting

        self.table.setRowCount(len(self.filtered_logs))

        for row, log in enumerate(self.filtered_logs):
            self.table.setItem(row, 0, self.add_table_item(row, 0, log.get("employee_id", "")))
            self.table.setItem(row, 1, self.add_table_item(row, 1, log.get("name", "")))
            self.table.setItem(row, 2, self.add_table_item(row, 2,log.get("department", "")))
            self.table.setItem(row, 3, self.add_table_item(row, 3,log.get("date", "")))
            self.table.setItem(row, 4, self.add_table_item(row, 4,log.get("status", "")))
            self.table.setItem(row, 5, self.add_table_item(row, 5,log.get("timestamp", "")))

        self.table.setSortingEnabled(True) # Re-enable sorting after population
   