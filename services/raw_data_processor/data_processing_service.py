import json
import sys

from dotenv import load_dotenv

load_dotenv(override=False)

from extractors import extract_cars_from_html
from fetchers import get_fetcher
from publishers import S3Publisher
from queue_service import SQSQueueService


def process_message(message: dict) -> list[dict]:
    """Given an SQS message describing a run, fetch all HTML and extract every car."""
    run_id = message["run_id"]
    print(f"Processing run {run_id} (backend={message.get('storage_backend')})")

    fetcher = get_fetcher(message)
    all_cars = []

    for html in fetcher.get_htmls():
        cars = extract_cars_from_html(html)
        print(f"  Extracted {len(cars)} cars")
        all_cars.extend(cars)

    publisher = S3Publisher()
    s3_uri = publisher.publish(run_id, all_cars)

    queue = SQSQueueService()
    queue.publish({
        "run_id": run_id,
        "cars_extracted": len(all_cars),
        "s3_uri": s3_uri,
        "bucket": publisher.bucket,
        "key": f"processed/{run_id}/cars.parquet",
        "source_url": message.get("source_url"),
        "country": message.get("country"),
    })

    return all_cars


def lambda_handler(event, _context):
    for record in event["Records"]:
        message = json.loads(record["body"])
        process_message(message)


if __name__ == "__main__":
    # For local testing: pass a JSON file containing the SQS message
    # Example: python data_processing_service.py test_message.json
    if len(sys.argv) < 2:
        print("Usage: python data_processing_service.py <path-to-message.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        message = json.load(f)

    cars = process_message(message)

    print(f"\nTotal cars in run {message['run_id']}: {len(cars)}")
    if cars:
        print(f"First car: {cars[0]['title']} (id={cars[0]['id']})")
        print(f"Last car:  {cars[-1]['title']} (id={cars[-1]['id']})")