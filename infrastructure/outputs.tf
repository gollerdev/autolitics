output "bucket_name" {
  value = aws_s3_bucket.data.bucket
}

output "queue_url" {
  value = aws_sqs_queue.raw_queue.url
}

output "aws_access_key_id" {
  value = aws_iam_access_key.app.id
}

output "aws_secret_access_key" {
  value     = aws_iam_access_key.app.secret
  sensitive = true
}

output "ecr_repository_url" {
  value = aws_ecr_repository.ingestor.repository_url
}

output "processed_bucket_name" {
  value = aws_s3_bucket.processed.bucket
}

output "processed_queue_url" {
  value = aws_sqs_queue.processed_queue.url
}