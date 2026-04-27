import boto3
import os
from dotenv import load_dotenv



class S3StorageService:
    """Stores files in AWS S3.
    Drop-in replacement for LocalStorageService when running on AWS.
    """

    def __init__(self, base_path: str = None):
        self.bucket = os.getenv("S3_BUCKET")
        self.client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def save(self, key: str, content: str | bytes) -> str:
        """Upload content to S3. Key is the S3 object key e.g. 'raw/run_id/offset_0.html'.
        Returns the S3 URI where the file was saved."""
        if isinstance(content, str):
            content = content.encode("utf-8")

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
        )

        return f"s3://{self.bucket}/{key}"
    
