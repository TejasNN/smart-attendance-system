from datetime import datetime, time, timedelta, timezone

class ShiftPolicy:
    """
    Encapsulates office shift timings and remarks logic.
    Handles timezone (UTC→IST) and defines early/on-time/late.
    """

    def __init__(self, start_hour: int = 9, start_minute: int = 0, grace_minutes: int = 1):
        # default shift: 9:00 AM IST
        self.shift_start_time = time(hour=start_hour, minute=start_minute)
        self.grace_minutes = grace_minutes

    def get_remarks(self, timestamp: datetime) -> str:
        """
        Given a timestamp, determine the remark: early, on-time, late.
        """
        # convert utc timstamp to IST
        ist_offset = timedelta(hours=5, minutes=30)
        ist_time = timestamp.astimezone(timezone(ist_offset)).time()

        # Define start and grace_end window
        shift_start = self.shift_start_time
        shift_grace_end = (
            datetime.combine(datetime.today(), shift_start) + timedelta(minutes=self.grace_minutes)
        ).time()

        if ist_time < shift_start:
            return "early"
        elif shift_start <= ist_time <= shift_grace_end:
            return "on-time"
        else:
            return "late"