from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
    QLineEdit, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from datetime import datetime, timedelta
from desktop_app.utils.utils import ( 
    current_date_utc_midnight,
    get_ist_time_from_utc, get_ist_date_from_utc
)

class LogsWindow(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Attendance Logs")
        self.resize(800, 500)

        self.all_logs = []          # store all logs fetched from MongoDB
        self.filtered_logs = []     # store filtered logs based on search/filter

        main_layout = QVBoxLayout()

        # top control bar layout
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
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Employee ID", "Name", "Department","Date", "Status", "Timestamp", "Remarks", "Marked By"])

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
        today_utc = current_date_utc_midnight()

        if filter_option == "Today":
            start_date = today_utc
            end_date = start_date + timedelta(days=1)

        elif filter_option == "This Week":
            start_date = today_utc - timedelta(days=today_utc.weekday())
            end_date = start_date + timedelta(days=7)

        elif filter_option == "This Month":
            start_date = today_utc.replace(day=1)
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1)                  
        else:
            start_date = end_date = None

        # Build mongodb query
        query = {}
        if start_date and end_date:
            query["attendance.date"] = {"$gte": start_date, "$lt": end_date}

        # Fetch logs
        raw_logs = list(self.db.collection.find(query).sort("attendance.date", -1)) # Sort by the most recent

        # Flatten and convert times to IST
        self.all_logs = [self.flatten_log(log) for log in raw_logs]

        # Apply search filters
        self.apply_filters()    


    def apply_filters(self):
        """Apply search-based filtering to logs"""
        search_text = self.search_box.text().lower().strip()

        if not search_text:
            self.filtered_logs = self.all_logs
        else:
            self.filtered_logs = [
                log for log in self.all_logs
                if any(search_text in str(value).lower() for value in log.values())
            ]
        self.update_table()


    def reset_filters(self) -> None:
        """Reset search box, date filter, header sorting, and reload all logs."""
        self.btn_reset_filter.setEnabled(False)

        # Clear search and date filters
        self.search_box.clear()
        self.date_filter.setCurrentIndex(0)

        # Reset all column header sorts
        header = self.table.horizontalHeader()
        self.table.setSortingEnabled(False)
        header.setSortIndicatorShown(False)
        header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

        # Reload all logs
        self.load_logs()
        
        self.table.setSortingEnabled(True)  # Re-enable sorting
        header.setSortIndicatorShown(True)

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
            self.table.setItem(row, 2, self.add_table_item(row, 2, log.get("department", "")))
            self.table.setItem(row, 3, self.add_table_item(row, 3, log.get("date", "")))
            self.table.setItem(row, 4, self.add_table_item(row, 4, log.get("status", "")))
            self.table.setItem(row, 5, self.add_table_item(row, 5, log.get("timestamp", "")))
            self.table.setItem(row, 6, self.add_table_item(row, 6, log.get("remarks", "")))
            self.table.setItem(row, 7, self.add_table_item(row, 7, log.get("marked_by", "")))

        self.table.setSortingEnabled(True) # Re-enable sorting after population


    def flatten_log(self, log: dict) -> dict:
        """Flatten nested MongoDB log document for display/export."""
        employee = log.get("employee", {})
        attendance = log.get("attendance", {})
        timestamp = log.get("timestamp", "")

        flattened =  {
            "employee_id": employee.get("id", ""),
            "name": employee.get("name", ""),
            "department": employee.get("department", ""),
            "date": attendance.get("date", ""),
            "status": attendance.get("status", ""),
            "remarks": attendance.get("remarks", ""),
            "marked_by": attendance.get("marked_by", ""),
            "timestamp": timestamp
        }  

        # Convert UTC -> IST for display
        if isinstance(flattened["timestamp"], datetime):
            flattened["timestamp"] = get_ist_time_from_utc(flattened["timestamp"])
        if isinstance(flattened["date"], datetime):
            flattened["date"] = get_ist_date_from_utc(flattened["date"])

        return flattened
   