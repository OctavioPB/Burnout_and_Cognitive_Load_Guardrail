resource "aws_security_group" "kafka" {
  name        = "${var.cluster_name}-msk-sg"
  description = "MSK cluster security group — internal access only"
  vpc_id      = var.vpc_id

  ingress {
    description = "Kafka plaintext (internal)"
    from_port   = 9092
    to_port     = 9092
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  ingress {
    description = "Kafka TLS (internal)"
    from_port   = 9094
    to_port     = 9094
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  ingress {
    description = "Zookeeper (internal)"
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.cluster_name}-msk-sg" }
}

resource "aws_msk_configuration" "main" {
  name              = "${var.cluster_name}-config"
  kafka_versions    = [var.kafka_version]

  server_properties = <<-PROPS
    auto.create.topics.enable=false
    default.replication.factor=3
    min.insync.replicas=2
    num.io.threads=8
    num.network.threads=5
    num.partitions=3
    num.replica.fetchers=2
    replica.lag.time.max.ms=30000
    socket.receive.buffer.bytes=102400
    socket.request.max.bytes=104857600
    socket.send.buffer.bytes=102400
    unclean.leader.election.enable=false
    zookeeper.session.timeout.ms=18000
  PROPS
}

resource "aws_msk_cluster" "main" {
  cluster_name           = var.cluster_name
  kafka_version          = var.kafka_version
  number_of_broker_nodes = var.number_of_broker_nodes

  broker_node_group_info {
    instance_type  = var.broker_instance_type
    client_subnets = var.private_subnets
    storage_info {
      ebs_storage_info { volume_size = var.broker_storage_volume_gb }
    }
    security_groups = [aws_security_group.kafka.id]
  }

  configuration_info {
    arn      = aws_msk_configuration.main.arn
    revision = aws_msk_configuration.main.latest_revision
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  logging {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = "/aws/msk/${var.cluster_name}"
      }
    }
  }

  tags = { Name = var.cluster_name }
}
