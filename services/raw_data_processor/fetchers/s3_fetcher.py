import os
from typing import Iterator
 
import boto3
 
from .base_fetcher import BaseFetcher
 
 
class S3Fetcher(BaseFetcher):
    """Reads run HTML files from AWS S3.
    Uses bucket and base_path directly from the SQS message."""
 
    def __init__(self, message: dict):
        super().__init__(message)
        self.bucket = message["bucket"]
        self.client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-2"))
 
    def get_htmls(self) -> Iterator[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        keys = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.base_path):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".html"):
                    keys.append(obj["Key"])
 
        keys.sort()
        print(f"Found {len(keys)} HTML files in s3://{self.bucket}/{self.base_path}")
 
        for key in keys:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            yield response["Body"].read().decode("utf-8")