from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from threads.absentee_marker import AbsenteeWorker
from utils.logger_config import setup_scheduler_logger
from database.mongo_db import MongoDB
from database.postgres_db import PostgresDB


class SchedulerManager:
    def __init__(self):
        self.mongo_db = MongoDB()
        self.postgres_db = PostgresDB()
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.logger = setup_scheduler_logger()
        
    def start(self):
        """Start the scheduler with all defined jobs."""
        self.logger.info("Starting background scheduler...")

        # Schedule daily absentee marking at 4:30 PM IST (11:00 AM UTC)
        self.scheduler.add_job(
            self.mark_absentees_daily,
            CronTrigger(hour=11, minute=0, timezone="UTC"),
            id="mark_absentee_job",
            replace_existing=True
        )
        self.scheduler.start()
        self.logger.info("Scheduler started successfully and absentee job added.")

    def mark_absentees_daily(self):
        """Automatically mark absentees."""
        try:
            self.logger.info(f"Running automatic absentee marking at {datetime.now()}")
            service = AbsenteeWorker(self.postgres_db, self.mongo_db, marked_by="System")
            service.run()
            self.logger.info("Automatic absentee marking completed successfully.")
            
        except Exception as e:
            self.logger.error(f"Error while marking absentee automatically: {e}", exc_info=True)
    
    
    def shutdown(self):
        """Gracefully shutdown the scheduler."""
        self.logger.info("Shutting down scheduler.")
        self.scheduler.shutdown(wait=False)
            