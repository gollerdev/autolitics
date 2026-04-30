variable "aws_region" {
  default = "us-east-2"
}

variable "bucket_name" {
  default = "autolitics-data"
}

variable "queue_name" {
  default = "autolitics-raw-queue"
}

variable "app_user_name" {
  default = "autolitics-app"
}

variable "processed_bucket_name" {
  default = "autolitics-processed"
}

variable "processed_queue_name" {
  default = "autolitics-processed-queue"
}

variable "db_name" {
  default = "autolitics"
}

variable "db_username" {
  default = "autolitics"
}

variable "db_password" {
  sensitive = true
}