# AWS Lambda ECR Deployment System

A production-grade system for deploying ECR container images to AWS Lambda functions with S3 access and VPC configuration.

## Overview

This system provides a comprehensive solution for deploying container images from Amazon ECR to AWS Lambda functions. It handles all aspects of the deployment process, including IAM role management, S3 bucket access configuration, and optional VPC integration.

## Features

1. **ECR Image Deployment**: Deploy container images from ECR to Lambda functions
2. **IAM Role Management**: Create, update, or reuse IAM roles and policies for Lambda functions
3. **S3 Bucket Access**: Configure Lambda functions with access to S3 buckets
4. **VPC Configuration**: Optionally bind Lambda functions to existing VPCs
5. **Idempotent Operations**: Safely handle repeated deployments

## Prerequisites

Before using this system, ensure you have:

1. **AWS Credentials**: Configured AWS credentials with appropriate permissions
   ```bash
   aws configure
   ```

2. **ECR Image**: A container image pushed to Amazon ECR
   ```bash
   aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.<region>.amazonaws.com
   docker tag <image_name>:<tag> <aws_account_id>.dkr.ecr.<region>.amazonaws.com/<repository_name>:<tag>
   docker push <aws_account_id>.dkr.ecr.<region>.amazonaws.com/<repository_name>:<tag>
   ```

3. **S3 Bucket**: An existing S3 bucket that the Lambda function will access
   ```bash
   aws s3 ls s3://<bucket_name>
   ```

4. **Python 3.8+**: Required for running the deployment system

## Installation

```bash
# Install from the repository
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## System Architecture

### Components

The system consists of the following components:

- **IAM Manager**: Handles creation, validation, and cleanup of IAM roles and policies
- **Lambda Deployer**: Manages Lambda function deployment from ECR images
- **S3 Access Manager**: Configures S3 bucket access for Lambda functions
- **VPC Configurator**: Handles VPC configuration for Lambda functions
- **CLI Interface**: Provides a command-line interface for the deployment system

### Workflow

1. User provides ECR image URI, Lambda function configuration, S3 bucket details, and optional VPC configuration
2. System checks for existing IAM roles and policies, removing conflicting ones if necessary
3. System creates or updates IAM roles with appropriate policies for S3 access
4. System deploys the ECR image to a Lambda function with the configured IAM role
5. If specified, system configures the Lambda function with VPC access

## Detailed Component Descriptions

### IAM Role Management

The IAM Role Manager handles the creation and management of IAM roles and policies for Lambda functions:

- **Role Creation**: Creates IAM roles with the necessary trust relationship for Lambda execution
- **Policy Management**: Creates and attaches policies for S3 bucket access
- **Conflict Resolution**: Detects and resolves conflicts with existing roles and policies
- **Force Recreation**: Optionally forces recreation of roles and policies even if they exist

When a role already exists, the system can:
1. Use the existing role (default behavior)
2. Update the existing role with new policies
3. Delete and recreate the role (with `force_recreate=True`)

### S3 Bucket Access Configuration

The S3 Access Manager configures Lambda functions to access S3 buckets:

- **Bucket Validation**: Verifies that the specified S3 bucket exists and is accessible
- **Environment Variables**: Sets environment variables in the Lambda function for bucket access
- **Access Testing**: Tests the Lambda function's ability to access the S3 bucket
- **Policy Configuration**: Works with the IAM Manager to ensure proper S3 access policies

The S3 bucket path is always passed as a parameter and never hardcoded, allowing for flexibility in bucket selection.

### VPC Configuration

The VPC Configurator enables Lambda functions to be deployed within an existing VPC:

- **VPC Validation**: Verifies that the specified VPC exists and is accessible
- **Subnet Configuration**: Configures the Lambda function to use specific subnets within the VPC
- **Security Group Configuration**: Applies security groups to the Lambda function
- **Network Interface Management**: Handles the creation and management of Elastic Network Interfaces

## Usage

### Command Line Interface

```bash
# Basic usage
lambda-deployer deploy --ecr-image-uri <ECR_IMAGE_URI> --function-name <FUNCTION_NAME> --s3-bucket <S3_BUCKET_NAME>

# With VPC configuration
lambda-deployer deploy --ecr-image-uri <ECR_IMAGE_URI> --function-name <FUNCTION_NAME> --s3-bucket <S3_BUCKET_NAME> --vpc-id <VPC_ID> --subnet-ids <SUBNET_ID1,SUBNET_ID2> --security-group-ids <SG_ID1,SG_ID2>

# Force recreate IAM role
lambda-deployer deploy --ecr-image-uri <ECR_IMAGE_URI> --function-name <FUNCTION_NAME> --s3-bucket <S3_BUCKET_NAME> --force-recreate-role

# Specify custom role name
lambda-deployer deploy --ecr-image-uri <ECR_IMAGE_URI> --function-name <FUNCTION_NAME> --s3-bucket <S3_BUCKET_NAME> --role-name <CUSTOM_ROLE_NAME>

# Configure Lambda memory and timeout
lambda-deployer deploy --ecr-image-uri <ECR_IMAGE_URI> --function-name <FUNCTION_NAME> --s3-bucket <S3_BUCKET_NAME> --memory-size 512 --timeout 60
```

### Python API

```python
from lambda_deployer.main import LambdaDeployer

# Initialize the deployer
deployer = LambdaDeployer()

# Deploy without VPC
result = deployer.deploy(
    ecr_image_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest",
    function_name="my-lambda-function",
    s3_bucket="my-s3-bucket"
)

# Deploy with VPC
result = deployer.deploy(
    ecr_image_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest",
    function_name="my-lambda-function",
    s3_bucket="my-s3-bucket",
    vpc_id="vpc-12345",
    subnet_ids=["subnet-12345", "subnet-67890"],
    security_group_ids=["sg-12345"]
)

# Print the results
print(f"Function ARN: {result['function_arn']}")
print(f"Role ARN: {result['role_arn']}")
```

## Parameter Reference

### Required Parameters

- `ecr_image_uri`: URI of the ECR image to deploy (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest`)
- `function_name`: Name of the Lambda function to create or update
- `s3_bucket`: Name of the S3 bucket to grant access to

### Optional Parameters

- `role_name`: Custom IAM role name (default: `{function_name}-role`)
- `force_recreate_role`: Whether to force recreation of the IAM role (default: `False`)
- `memory_size`: Lambda function memory size in MB (default: `128`)
- `timeout`: Lambda function timeout in seconds (default: `30`)
- `vpc_id`: ID of the VPC to bind the Lambda function to
- `subnet_ids`: List of subnet IDs for VPC configuration
- `security_group_ids`: List of security group IDs for VPC configuration

## Troubleshooting

### Common Issues

1. **IAM Permission Errors**
   - **Symptom**: `AccessDenied` or `UnauthorizedOperation` errors
   - **Solution**: Ensure your AWS credentials have the necessary permissions for IAM, Lambda, ECR, and S3 operations

2. **ECR Image Not Found**
   - **Symptom**: `ResourceNotFoundException` when deploying the Lambda function
   - **Solution**: Verify the ECR image URI is correct and the image exists in your ECR repository

3. **S3 Bucket Access Issues**
   - **Symptom**: Lambda function cannot access the S3 bucket
   - **Solution**: Check the IAM role policies and ensure the S3 bucket exists and is accessible

4. **VPC Configuration Errors**
   - **Symptom**: Lambda function deployment fails with VPC-related errors
   - **Solution**: Verify the VPC, subnet, and security group IDs are correct and the subnets have internet access

### Debugging

Enable verbose logging for more detailed information:

```bash
lambda-deployer deploy --ecr-image-uri <ECR_IMAGE_URI> --function-name <FUNCTION_NAME> --s3-bucket <S3_BUCKET_NAME> --verbose
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=lambda_deployer

# Run linting
flake8 src tests

# Run type checking
mypy src
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
