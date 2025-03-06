#!/usr/bin/env python3
"""
Example script for deploying an ECR image to AWS Lambda with S3 access and VPC configuration.
"""
import argparse
import logging
import sys

from lambda_deployer.main import LambdaDeployer


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Example script for deploying an ECR image to AWS Lambda with S3 access and VPC configuration"
    )
    
    parser.add_argument(
        "--ecr-image-uri", 
        required=True, 
        help="URI of the ECR image to deploy"
    )
    parser.add_argument(
        "--function-name", 
        required=True, 
        help="Name of the Lambda function"
    )
    parser.add_argument(
        "--s3-bucket", 
        required=True, 
        help="S3 bucket to grant access to"
    )
    
    # VPC configuration (optional)
    parser.add_argument(
        "--vpc-id", 
        help="VPC ID to bind the Lambda function to"
    )
    parser.add_argument(
        "--subnet-ids", 
        help="Comma-separated list of subnet IDs for VPC configuration"
    )
    parser.add_argument(
        "--security-group-ids", 
        help="Comma-separated list of security group IDs for VPC configuration"
    )
    
    # General options
    parser.add_argument(
        "--verbose", 
        "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point for the example script."""
    args = parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting example deployment")
    
    try:
        # Parse subnet IDs and security group IDs if provided
        subnet_ids = args.subnet_ids.split(",") if args.subnet_ids else None
        security_group_ids = args.security_group_ids.split(",") if args.security_group_ids else None
        
        # Create Lambda Deployer
        deployer = LambdaDeployer()
        
        # Deploy Lambda function
        result = deployer.deploy(
            ecr_image_uri=args.ecr_image_uri,
            function_name=args.function_name,
            s3_bucket=args.s3_bucket,
            vpc_id=args.vpc_id,
            subnet_ids=subnet_ids,
            security_group_ids=security_group_ids
        )
        
        logger.info(f"Successfully deployed Lambda function: {result['function_arn']}")
        logger.info(f"Using IAM role: {result['role_arn']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
