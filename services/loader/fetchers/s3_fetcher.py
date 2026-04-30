import io
import os
import boto3
import pyarrow.parquet as pq


class S3Fetcher:
    def __init__(self):
        self.client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-2"))

    def fetch(self, bucket: str, key: str) -> list[dict]:
        response = self.client.get_object(Bucket=bucket, Key=key)
        buffer = io.BytesIO(response["Body"].read())
        table = pq.read_table(buffer)
        return table.to_pylist()
