# ECR repository for the processor image
resource "aws_ecr_repository" "processor" {
  name                 = "autolitics-processor"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM role for the Lambda
resource "aws_iam_role" "lambda_processor_role" {
  name = "autolitics-processor-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_processor_policy" {
  name = "autolitics-processor-policy"
  role = aws_iam_role.lambda_processor_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [aws_s3_bucket.data.arn, "${aws_s3_bucket.data.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = ["${aws_s3_bucket.processed.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.raw_queue.arn
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = aws_sqs_queue.processed_queue.arn
      }
    ]
  })
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "processor" {
  name              = "/aws/lambda/autolitics-processor"
  retention_in_days = 7
}

# Lambda function — container image from ECR
resource "aws_lambda_function" "processor" {
  function_name = "autolitics-processor"
  role          = aws_iam_role.lambda_processor_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.processor.repository_url}:latest"
  timeout       = 300
  memory_size   = 512

  environment {
    variables = {
      PROCESSED_BUCKET    = aws_s3_bucket.processed.bucket
      PROCESSED_QUEUE_URL = aws_sqs_queue.processed_queue.url
    }
  }

  depends_on = [aws_cloudwatch_log_group.processor]
}

# Trigger: fire Lambda for every message on the raw queue
resource "aws_lambda_event_source_mapping" "processor_trigger" {
  event_source_arn = aws_sqs_queue.raw_queue.arn
  function_name    = aws_lambda_function.processor.arn
  batch_size       = 1
}
