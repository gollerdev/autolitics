import json
import sys

from dotenv import load_dotenv

load_dotenv(override=False)

from fetchers.s3_fetcher import S3Fetcher
from publishers.postgres_publisher import PostgresPublisher


def process_message(message: dict) -> None:
    run_id = message["run_id"]
    bucket = message["bucket"]
    key    = message["key"]

    fetcher = S3Fetcher()
    cars = fetcher.fetch(bucket, key)
    print(f"Fetched {len(cars)} cars from s3://{bucket}/{key}")

    publisher = PostgresPublisher()
    try:
        publisher.insert_staging(cars, run_id)
        publisher.insert_normalized(cars, run_id)
    finally:
        publisher.close()


def lambda_handler(event, _context):
    for record in event["Records"]:
        message = json.loads(record["body"])
        process_message(message)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python data_loading_service.py <path-to-message.json>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        message = json.load(f)
    process_message(message)
