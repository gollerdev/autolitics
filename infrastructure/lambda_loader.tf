# ECR repository for the loader image
resource "aws_ecr_repository" "loader" {
  name                 = "autolitics-loader"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM role for the Lambda
resource "aws_iam_role" "lambda_loader_role" {
  name = "autolitics-loader-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_loader_policy" {
  name = "autolitics-loader-policy"
  role = aws_iam_role.lambda_loader_role.id

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
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.processed.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.processed_queue.arn
      }
    ]
  })
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "loader" {
  name              = "/aws/lambda/autolitics-loader"
  retention_in_days = 7
}

# Lambda function — container image from ECR
resource "aws_lambda_function" "loader" {
  function_name = "autolitics-loader"
  role          = aws_iam_role.lambda_loader_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.loader.repository_url}:latest"
  timeout       = 300
  memory_size   = 512

  environment {
    variables = {
      DB_HOST = aws_db_instance.main.address
      DB_PORT = "5432"
      DB_NAME = var.db_name
      DB_USER = var.db_username
      DB_PASSWORD = var.db_password
    }
  }

  depends_on = [aws_cloudwatch_log_group.loader]
}

# Trigger: fire Lambda for every message on the processed queue
resource "aws_lambda_event_source_mapping" "loader_trigger" {
  event_source_arn = aws_sqs_queue.processed_queue.arn
  function_name    = aws_lambda_function.loader.arn
  batch_size       = 1
}
