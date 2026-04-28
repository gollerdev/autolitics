# ECR Repository
resource "aws_ecr_repository" "ingestor" {
  name                 = "autolitics-ingestor"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "autolitics"
}

# IAM Role for ECS Task Execution (pull from ECR, write logs)
resource "aws_iam_role" "ecs_execution_role" {
  name = "autolitics-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Task (access S3, SQS at runtime)
resource "aws_iam_role" "ecs_task_role" {
  name = "autolitics-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_role_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.app_policy.arn
}

# ECS Task Definition
resource "aws_ecs_task_definition" "ingestor" {
  family                   = "autolitics-ingestor"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"  # 1 vCPU
  memory                   = "2048"  # 2GB
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name      = "ingestor"
    image     = "${aws_ecr_repository.ingestor.repository_url}:latest"
    essential = true

    environment = [
      { name = "AWS_REGION",        value = var.aws_region },
      { name = "S3_BUCKET",         value = var.bucket_name },
      { name = "QUEUE_URL",         value = aws_sqs_queue.raw_queue.url },
      { name = "PROXY_SERVER",      value = "http://0.tcp.sa.ngrok.io:19835" },
      { name = "PROXY_USERNAME",    value = "" },
      { name = "PROXY_PASSWORD",    value = "" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/autolitics-ingestor"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# CloudWatch Log Group for ECS logs
resource "aws_cloudwatch_log_group" "ingestor" {
  name              = "/ecs/autolitics-ingestor"
  retention_in_days = 7
}

# VPC and Subnet (needed for Fargate networking)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# IAM Role for EventBridge Scheduler
resource "aws_iam_role" "scheduler_role" {
  name = "autolitics-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler_policy" {
  name = "autolitics-scheduler-policy"
  role = aws_iam_role.scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "ecs:RunTask"
      Resource = aws_ecs_task_definition.ingestor.arn
    },
    {
      Effect   = "Allow"
      Action   = "iam:PassRole"
      Resource = [
        aws_iam_role.ecs_execution_role.arn,
        aws_iam_role.ecs_task_role.arn
      ]
    }]
  })
}

# EventBridge Scheduler — every 2 hours, 8am-10pm Uruguay (UTC-3 = 11am-1am UTC)
resource "aws_scheduler_schedule" "ingestor" {
  name = "autolitics-ingestor-schedule"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 11,13,15,17,19,21,23 * * ? *)"
  schedule_expression_timezone = "America/Montevideo"

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.scheduler_role.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.ingestor.arn
      launch_type         = "FARGATE"

      network_configuration {
        assign_public_ip = true
        subnets          = data.aws_subnets.default.ids
      }
    }
  }
}

resource "aws_iam_role_policy" "ecs_execution_logs_policy" {
  name = "autolitics-ecs-logs-policy"
  role = aws_iam_role.ecs_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:CreateLogGroup"
      ]
      Resource = "${aws_cloudwatch_log_group.ingestor.arn}:*"
    }]
  })
}
