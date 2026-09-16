import argparse
import logging

from config import load_config
from database import insert_job_postings_and_get_new
from notification import send_combined_telegram_message
from scraper import fetch_combined_job_posts


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments containing the config file path.
    """
    parser = argparse.ArgumentParser(description="Fetch job postings based on configuration.")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        default="config.json",
        help="Path to the configuration JSON file (default: config.json)."
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)."
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="scraper.log",
        help="Path to the log file (default: scraper.log)."
    )
    return parser.parse_args()


def process_job_postings(combined_jobs_df, bot_token, chat_id):
    """
    Insert job postings into the database, log the results, and notify via Telegram.

    Args:
        combined_jobs_df (pd.DataFrame): DataFrame containing job postings.
        bot_token (str): Telegram bot token.
        chat_id (str): Telegram chat ID.
    """
    try:
        # Insert into the database and get new jobs
        new_jobs = insert_job_postings_and_get_new(combined_jobs_df)

        if not new_jobs.empty:
            logging.info(f"Inserted {len(new_jobs)} new job postings.")

            # Send a combined notification for all new jobs
            send_combined_telegram_message(bot_token, chat_id, new_jobs)
        else:
            logging.info("No new job postings were found.")

    except Exception as e:
        logging.error(f"Failed to process job postings: {e}")

def main():
    try:
        # Parse command-line arguments
        args = parse_arguments()

        # Initialize logging
        logging.basicConfig(
            filename=args.log_file,
            level=getattr(logging, args.log_level.upper(), "INFO"),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Load configuration from the specified config file
        config = load_config(args.config)

        # Validate configuration
        required_keys = ["job_titles", "locations", "country_indeed", "telegram"]
        for key in required_keys:
            if key not in config:
                logging.error(f"Missing key '{key}' in the configuration file.")
                return

        # Extract configuration values
        job_titles = config["job_titles"]
        locations = config["locations"]
        country_indeed = config["country_indeed"]
        import os
        telegram_config = config["telegram"]
        bot_token = telegram_config.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = telegram_config.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID", "")

        if not bot_token or not chat_id:
            logging.error("Telegram credentials missing.")
            return

        # Fetch combined job postings
        combined_jobs_df = fetch_combined_job_posts(job_titles, locations, country_indeed)

        # Process job postings and send notifications
        process_job_postings(combined_jobs_df, bot_token, chat_id)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
