import io
import os

import boto3
import pyarrow as pa
import pyarrow.parquet as pq


class S3Publisher:
    """Uploads processed car data as Parquet to the processed S3 bucket."""

    def __init__(self):
        self.bucket = os.getenv("PROCESSED_BUCKET")
        if not self.bucket:
            raise ValueError("PROCESSED_BUCKET env var is not set")
        self.client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-2"))

    @staticmethod
    def _sanitize(obj):
        """Replace empty dicts with None — Parquet can't represent structs with no fields."""
        if isinstance(obj, dict):
            return {k: S3Publisher._sanitize(v) for k, v in obj.items()} or None
        if isinstance(obj, list):
            return [S3Publisher._sanitize(item) for item in obj]
        return obj

    def publish(self, run_id: str, cars: list[dict]) -> str:
        """Serialize cars as Parquet and upload to S3. Returns the S3 URI."""
        key = f"processed/{run_id}/cars.parquet"

        table = pa.Table.from_pylist([self._sanitize(car) for car in cars])
        buffer = io.BytesIO()
        pq.write_table(table, buffer)

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=buffer.getvalue(),
            ContentType="application/octet-stream",
        )

        s3_uri = f"s3://{self.bucket}/{key}"
        print(f"Published {len(cars)} cars to {s3_uri}")
        return s3_uri
