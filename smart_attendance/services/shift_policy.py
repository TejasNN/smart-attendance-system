from datetime import datetime, time

class ShiftPolicy:
    """
    Encapsulates office shift timings and remarks logic.
    """

    def __init__(self, start_hour: int = 9, start_minute:int = 0):
        self.shift_start_time = time(hour=start_hour, minute=start_minute)

    @classmethod
    def get_remarks(self, timestamp: datetime) -> str:
        """
        Given a timestamp, determine the remark: early, on-time, late.
        """
        shift_start_datetime = timestamp.replace(
            hour=self.shift_start_time.hour,
            minute=self.shift_start_time.minute,
            second=0,
            microsecond=0
        )

        if timestamp < shift_start_datetime:
            return "early"
        elif timestamp > shift_start_datetime:
            return "late"
        else:
            return "on-time"