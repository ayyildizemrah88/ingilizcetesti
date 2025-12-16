# Skills Test Center - Terraform Infrastructure
# AWS-based infrastructure with auto-scaling

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Remote state storage (recommended for production)
  backend "s3" {
    bucket         = "skillstestcenter-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "eu-central-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "SkillsTestCenter"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ══════════════════════════════════════════════════════════════════
# VARIABLES
# ══════════════════════════════════════════════════════════════════

variable "aws_region" {
  description = "AWS region"
  default     = "eu-central-1"
}

variable "environment" {
  description = "Environment name"
  default     = "production"
}

variable "app_name" {
  description = "Application name"
  default     = "skillstestcenter"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# ══════════════════════════════════════════════════════════════════
# VPC & NETWORKING
# ══════════════════════════════════════════════════════════════════

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  
  name = "${var.app_name}-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  single_nat_gateway = true  # Use multiple for HA in production
  
  enable_dns_hostnames = true
  enable_dns_support   = true
}

# ══════════════════════════════════════════════════════════════════
# RDS PostgreSQL
# ══════════════════════════════════════════════════════════════════

resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-db-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "rds" {
  name        = "${var.app_name}-rds-sg"
  description = "RDS security group"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "main" {
  identifier        = "${var.app_name}-db"
  engine            = "postgres"
  engine_version    = "15"
  instance_class    = "db.t3.medium"
  allocated_storage = 100
  
  db_name  = "skillstestcenter"
  username = "admin"
  password = var.db_password
  
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  
  multi_az               = true  # High availability
  storage_encrypted      = true
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.app_name}-final-snapshot"
  
  performance_insights_enabled = true
}

# ══════════════════════════════════════════════════════════════════
# ElastiCache Redis
# ══════════════════════════════════════════════════════════════════

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.app_name}-redis-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "redis" {
  name        = "${var.app_name}-redis-sg"
  description = "Redis security group"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${var.app_name}-redis"
  description          = "Redis cluster for ${var.app_name}"
  
  node_type            = "cache.t3.medium"
  num_cache_clusters   = 2
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}

# ══════════════════════════════════════════════════════════════════
# S3 BUCKET
# ══════════════════════════════════════════════════════════════════

resource "aws_s3_bucket" "storage" {
  bucket = "${var.app_name}-storage-${var.aws_region}"
}

resource "aws_s3_bucket_versioning" "storage" {
  bucket = aws_s3_bucket.storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  rule {
    id     = "cleanup_old_recordings"
    status = "Enabled"
    
    filter {
      prefix = "audio/"
    }
    
    expiration {
      days = 365  # KVKK compliance
    }
  }
}

# ══════════════════════════════════════════════════════════════════
# ECS CLUSTER (Alternative to Kubernetes)
# ══════════════════════════════════════════════════════════════════

resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_security_group" "app" {
  name        = "${var.app_name}-app-sg"
  description = "Application security group"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ══════════════════════════════════════════════════════════════════
# OUTPUTS
# ══════════════════════════════════════════════════════════════════

output "database_endpoint" {
  value       = aws_db_instance.main.endpoint
  description = "RDS endpoint"
}

output "redis_endpoint" {
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  description = "Redis endpoint"
}

output "s3_bucket" {
  value       = aws_s3_bucket.storage.bucket
  description = "S3 bucket name"
}

output "vpc_id" {
  value       = module.vpc.vpc_id
  description = "VPC ID"
}
