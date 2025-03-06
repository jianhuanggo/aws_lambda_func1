#!/usr/bin/env python3
"""
Command-line interface for the Lambda Deployer system.
"""
import argparse
import logging
import sys
from typing import List, Optional

from lambda_deployer.iam.role_manager import IAMRoleManager
from lambda_deployer.lambda_func.function_deployer import LambdaFunctionDeployer
from lambda_deployer.s3.access_manager import S3AccessManager
from lambda_deployer.vpc.configurator import VPCConfigurator


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Deploy ECR images to AWS Lambda functions with S3 access and VPC configuration"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy an ECR image to a Lambda function")
    deploy_parser.add_argument(
        "--ecr-image-uri", 
        required=True, 
        help="URI of the ECR image to deploy"
    )
    deploy_parser.add_argument(
        "--function-name", 
        required=True, 
        help="Name of the Lambda function"
    )
    deploy_parser.add_argument(
        "--s3-bucket", 
        required=True, 
        help="S3 bucket to grant access to"
    )
    deploy_parser.add_argument(
        "--memory-size", 
        type=int, 
        default=128, 
        help="Memory size for the Lambda function in MB (default: 128)"
    )
    deploy_parser.add_argument(
        "--timeout", 
        type=int, 
        default=30, 
        help="Timeout for the Lambda function in seconds (default: 30)"
    )
    
    # VPC configuration (optional)
    deploy_parser.add_argument(
        "--vpc-id", 
        help="VPC ID to bind the Lambda function to"
    )
    deploy_parser.add_argument(
        "--subnet-ids", 
        help="Comma-separated list of subnet IDs for VPC configuration"
    )
    deploy_parser.add_argument(
        "--security-group-ids", 
        help="Comma-separated list of security group IDs for VPC configuration"
    )
    
    # IAM role options
    deploy_parser.add_argument(
        "--role-name", 
        help="Name of the IAM role to create or use (default: derived from function name)"
    )
    deploy_parser.add_argument(
        "--force-recreate-role", 
        action="store_true", 
        help="Force recreation of IAM role even if it exists"
    )
    
    # General options
    parser.add_argument(
        "--verbose", 
        "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    return parser.parse_args(args)


def deploy_command(args: argparse.Namespace) -> int:
    """Handle the deploy command."""
    logger = logging.getLogger("lambda_deployer.cli")
    
    # Parse VPC configuration if provided
    vpc_config = None
    if args.vpc_id:
        if not args.subnet_ids:
            logger.error("--subnet-ids must be provided when using --vpc-id")
            return 1
        
        subnet_ids = args.subnet_ids.split(",")
        security_group_ids = args.security_group_ids.split(",") if args.security_group_ids else []
        
        vpc_configurator = VPCConfigurator()
        vpc_config = vpc_configurator.create_vpc_config(
            vpc_id=args.vpc_id,
            subnet_ids=subnet_ids,
            security_group_ids=security_group_ids
        )
    
    # Set up IAM role for Lambda function
    role_name = args.role_name or f"lambda-{args.function_name}-role"
    iam_manager = IAMRoleManager()
    
    try:
        role_arn = iam_manager.create_or_update_role(
            role_name=role_name,
            s3_bucket=args.s3_bucket,
            force_recreate=args.force_recreate_role
        )
    except Exception as e:
        logger.error(f"Failed to create or update IAM role: {e}")
        return 1
    
    # Deploy Lambda function
    lambda_deployer = LambdaFunctionDeployer()
    try:
        function_arn = lambda_deployer.deploy_function(
            function_name=args.function_name,
            ecr_image_uri=args.ecr_image_uri,
            role_arn=role_arn,
            memory_size=args.memory_size,
            timeout=args.timeout,
            vpc_config=vpc_config
        )
        logger.info(f"Successfully deployed Lambda function: {function_arn}")
    except Exception as e:
        logger.error(f"Failed to deploy Lambda function: {e}")
        return 1
    
    # Configure S3 access
    s3_manager = S3AccessManager()
    try:
        s3_manager.configure_s3_access(
            function_name=args.function_name,
            s3_bucket=args.s3_bucket
        )
        logger.info(f"Successfully configured S3 access for Lambda function")
    except Exception as e:
        logger.error(f"Failed to configure S3 access: {e}")
        return 1
    
    return 0


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    parsed_args = parse_args(args)
    setup_logging(parsed_args.verbose)
    
    if parsed_args.command == "deploy":
        return deploy_command(parsed_args)
    else:
        print("No command specified. Use --help for usage information.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
