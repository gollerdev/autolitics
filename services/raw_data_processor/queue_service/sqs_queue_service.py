import json
import os
from datetime import datetime

import boto3


class SQSQueueService:
    """Enqueues processed-run metadata to SQS for the loader service to consume."""

    def __init__(self):
        self.queue_url = os.getenv("PROCESSED_QUEUE_URL")
        if not self.queue_url:
            raise ValueError("PROCESSED_QUEUE_URL env var is not set")
        self.client = boto3.client("sqs", region_name=os.getenv("AWS_REGION", "us-east-2"))

    def publish(self, message: dict) -> None:
        """Sends processed-run metadata to SQS."""
        message["enqueued_at"] = datetime.utcnow().isoformat()
        self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message, ensure_ascii=False),
        )
        print(f"  Enqueued processed run {message['run_id']} to SQS")
