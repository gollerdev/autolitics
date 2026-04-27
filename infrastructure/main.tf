provider "aws" {
  region = "us-east-2"
}

resource "aws_s3_bucket" "data" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# SQS queue
resource "aws_sqs_queue" "raw_queue" {
  name                      = var.queue_name
  message_retention_seconds = 86400
}

# IAM user for the app
resource "aws_iam_user" "app" {
  name = var.app_user_name
}

# IAM policy
resource "aws_iam_policy" "app_policy" {
  name = "autolitics-app-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.data.arn,
          "${aws_s3_bucket.data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage"]
        Resource = aws_sqs_queue.raw_queue.arn
      }
    ]
  })
}

# Attach policy to user
resource "aws_iam_user_policy_attachment" "app" {
  user       = aws_iam_user.app.name
  policy_arn = aws_iam_policy.app_policy.arn
}

# Access keys for the app user
resource "aws_iam_access_key" "app" {
  user = aws_iam_user.app.name
}
