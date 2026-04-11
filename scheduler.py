"""
Automated scheduler for daily ETF data collection.
Runs Tuesday to Saturday to collect data up to the last trading day.
"""

import schedule
import time
import logging
from datetime import datetime
from data_collection import run_collection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def should_run_today():
    """
    Check if the script should run today.
    Runs on Tuesday (1), Wednesday (2), Thursday (3), Friday (4), Saturday (5).
    Skips Sunday (6) and Monday (0).
    """
    weekday = datetime.now().weekday()
    return weekday in [1, 2, 3, 4, 5]

def scheduled_job():
    """
    Job to be run daily.
    """
    if should_run_today():
        logging.info("=" * 60)
        logging.info(f"Starting scheduled data collection at {datetime.now()}")
        logging.info("=" * 60)

        try:
            run_collection(use_dynamic_dates=True)
            logging.info("Scheduled data collection completed successfully")
        except Exception as e:
            logging.error(f"Error during scheduled collection: {e}")
    else:
        day_name = datetime.now().strftime('%A')
        logging.info(f"Skipping collection today ({day_name}) - Only runs Tuesday to Saturday")

def run_scheduler():
    """
    Sets up and runs the scheduler.
    Schedules the job to run daily at a specific time.
    """
    # Schedule to run every day at 6:00 PM (18:00)
    # Adjust this time as needed
    schedule.every().day.at("18:00").do(scheduled_job)

    logging.info("Scheduler started. Data collection will run Tuesday-Saturday at 18:00")
    logging.info("Press Ctrl+C to stop the scheduler")

    # Run immediately on startup if today is a valid day
    if should_run_today():
        logging.info("Running initial collection...")
        scheduled_job()

    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    run_scheduler()
