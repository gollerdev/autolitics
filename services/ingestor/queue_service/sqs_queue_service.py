import json
import os
import boto3
from datetime import datetime
from dotenv import load_dotenv
 
load_dotenv()
 
print(os.getenv("QUEUE_URL"))

class SQSQueueService:
    """Enqueues run metadata to AWS SQS for the parser service to consume."""
 
    def __init__(self):
        self.queue_url = os.getenv("QUEUE_URL")
        self.client = boto3.client(
            "sqs",
            region_name=os.getenv("AWS_REGION", "us-east-2"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
 
    def publish(self, message: dict) -> None:
        """Sends run metadata as a message to SQS."""
        message["enqueued_at"] = datetime.utcnow().isoformat()
 
        self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message, ensure_ascii=False),
        )
 
        print(f"  Enqueued run {message['run_id']} to SQS")