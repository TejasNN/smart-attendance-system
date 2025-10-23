import traceback
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
from services.attendance_record import AttendanceRecord


class AbsenteeWorkerSignals(QObject):
    step = pyqtSignal(str)      # step message string
    progress = pyqtSignal(int)  # percent or step index
    done = pyqtSignal(dict)     # final summary dict
    error = pyqtSignal(str)

class AbsenteeWorker(QRunnable):
    """
    Worker to compute absentees:
    Steps:
      1. fetch all employees from postgres
      2. fetch present ids from mongo for today
      3. compute absent ids
      4. prepare records and bulk insert into mongo
    Emits step messages and final summary.
    """
    def __init__(self, post_db, mongo_db, marked_by="Admin"):
        super().__init__()
        self.postgres_db = post_db
        self.mongo_db = mongo_db
        self.marked_by = marked_by
        self.signals = AbsenteeWorkerSignals()

    def run(self):
        try:
            # Step 1: fetch all employees
            self.signals.step.emit("Fetching registered employees...")
            all_employees = self.postgres_db.get_all_employees()
            total = len(all_employees)
            self.signals.progress.emit(10)

            # Step 2: fetch present employees from mongo for today
            self.signals.step.emit("Checking today's attendance records...")
            present_ids = self.mongo_db.get_present_employee_ids()
            present_count = len(present_ids)
            self.signals.progress.emit(30)

            # Step 3 : compute absentees
            self.signals.step.emit("Calculating absentees...")
            all_ids = {str(emp['employee_id']): emp for emp in all_employees}
            absent_ids = [eid for eid in all_ids.keys() if eid not in present_ids]
            absent_count = len(absent_ids)
            self.signals.progress.emit(50)

            if absent_count == 0:
                self.signals.step.emit("No absentees found. Nothing to do.")
                summary = {"total": total, "present": present_count, "absent_marked": 0, "skipped": 0}
                self.signals.done.emit(summary)
                return
            
            # Step 4 : Prepare records
            self.signals.step.emit(f"Preparing {absent_count} absentee records...")
            absent_records = []
            for eid in absent_ids:
                emp = all_ids[eid]

                record = AttendanceRecord(
                    employee_id=str(emp["employee_id"]),
                    name=emp.get("name"),
                    status="absent",
                    marked_by=self.marked_by
                )

                absent_records.append(record.to_dict())
            self.signals.progress.emit(75)

            # Step 5 : Bulk insert to mongoDB
            self.signals.step.emit("Saving absentees to database...")
            result = self.mongo_db.insert_absentees_bulk(absent_records)

            self.signals.progress.emit(100)
            summary = {
                "total": total,
                "present": present_count,
                "absent_to_mark": absent_count,
                "inserted": result.get("inserted", 0),
                "skipped": result.get("skipped", 0),
                "errors": result.get("errors", [])
            }
            self.signals.done.emit(summary)
        except Exception as e:
            trace = traceback.format_exc()
            self.signals.error.emit(f"{str(e)}\n{trace}")
            