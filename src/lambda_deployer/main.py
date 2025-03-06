#!/usr/bin/env python3
"""
Main deployment script for Lambda Deployer.

This module provides the main functionality for deploying ECR images to AWS Lambda functions
with S3 access and VPC configuration.
"""
import argparse
import logging
import sys
from typing import Dict, List, Optional

from lambda_deployer.iam.role_manager import IAMRoleManager
from lambda_deployer.lambda_func.function_deployer import LambdaFunctionDeployer
from lambda_deployer.s3.access_manager import S3AccessManager
from lambda_deployer.vpc.configurator import VPCConfigurator


class LambdaDeployer:
    """
    Main class for deploying ECR images to AWS Lambda functions.
    
    This class integrates all components of the Lambda Deployer system:
    - IAM role management
    - Lambda function deployment
    - S3 access configuration
    - VPC configuration
    """
    
    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize the Lambda Deployer.
        
        Args:
            region_name: AWS region name. If not provided, uses the default region.
        """
        self.region_name = region_name
        self.iam_manager = IAMRoleManager(region_name=region_name)
        self.lambda_deployer = LambdaFunctionDeployer(region_name=region_name)
        self.s3_manager = S3AccessManager(region_name=region_name)
        self.vpc_configurator = VPCConfigurator(region_name=region_name)
        self.logger = logging.getLogger(__name__)
    
    def deploy(
        self,
        ecr_image_uri: str,
        function_name: str,
        s3_bucket: str,
        role_name: Optional[str] = None,
        memory_size: int = 128,
        timeout: int = 30,
        vpc_id: Optional[str] = None,
        subnet_ids: Optional[List[str]] = None,
        security_group_ids: Optional[List[str]] = None,
        force_recreate_role: bool = False
    ) -> Dict[str, str]:
        """
        Deploy an ECR image to a Lambda function with S3 access and optional VPC configuration.
        
        Args:
            ecr_image_uri: URI of the ECR image to deploy
            function_name: Name of the Lambda function
            s3_bucket: Name of the S3 bucket to grant access to
            role_name: Name of the IAM role to create or use (default: derived from function name)
            memory_size: Memory size for the Lambda function in MB (default: 128)
            timeout: Timeout for the Lambda function in seconds (default: 30)
            vpc_id: VPC ID to bind the Lambda function to (optional)
            subnet_ids: List of subnet IDs for VPC configuration (required if vpc_id is provided)
            security_group_ids: List of security group IDs for VPC configuration (optional)
            force_recreate_role: Force recreation of IAM role even if it exists (default: False)
            
        Returns:
            Dictionary containing deployment information (function_arn, role_arn)
            
        Raises:
            ValueError: If required parameters are invalid
        """
        # Validate parameters
        if not ecr_image_uri:
            raise ValueError("ECR image URI is required")
        
        if not function_name:
            raise ValueError("Function name is required")
        
        if not s3_bucket:
            raise ValueError("S3 bucket name is required")
        
        # Set default role name if not provided
        if not role_name:
            role_name = f"lambda-{function_name}-role"
        
        # Process VPC configuration if provided
        vpc_config = None
        if vpc_id:
            if not subnet_ids:
                raise ValueError("Subnet IDs must be provided when using VPC configuration")
            
            self.logger.info(f"Creating VPC configuration for VPC {vpc_id}")
            vpc_config = self.vpc_configurator.create_vpc_config(
                vpc_id=vpc_id,
                subnet_ids=subnet_ids,
                security_group_ids=security_group_ids
            )
        
        # Create or update IAM role
        self.logger.info(f"Creating or updating IAM role {role_name}")
        role_arn = self.iam_manager.create_or_update_role(
            role_name=role_name,
            s3_bucket=s3_bucket,
            force_recreate=force_recreate_role
        )
        
        # Deploy Lambda function
        self.logger.info(f"Deploying Lambda function {function_name} from ECR image {ecr_image_uri}")
        function_arn = self.lambda_deployer.deploy_function(
            function_name=function_name,
            ecr_image_uri=ecr_image_uri,
            role_arn=role_arn,
            memory_size=memory_size,
            timeout=timeout,
            vpc_config=vpc_config
        )
        
        # Configure S3 access
        self.logger.info(f"Configuring S3 access for Lambda function {function_name} to bucket {s3_bucket}")
        self.s3_manager.configure_s3_access(
            function_name=function_name,
            s3_bucket=s3_bucket
        )
        
        # Return deployment information
        return {
            "function_arn": function_arn,
            "role_arn": role_arn
        }


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
        description="Deploy ECR images to AWS Lambda functions with S3 access and VPC configuration"
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
    parser.add_argument(
        "--memory-size", 
        type=int, 
        default=128, 
        help="Memory size for the Lambda function in MB (default: 128)"
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=30, 
        help="Timeout for the Lambda function in seconds (default: 30)"
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
    
    # IAM role options
    parser.add_argument(
        "--role-name", 
        help="Name of the IAM role to create or use (default: derived from function name)"
    )
    parser.add_argument(
        "--force-recreate-role", 
        action="store_true", 
        help="Force recreation of IAM role even if it exists"
    )
    
    # Region option
    parser.add_argument(
        "--region", 
        help="AWS region to use"
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
    """Main entry point for the script."""
    args = parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Lambda Deployer")
    
    try:
        # Parse subnet IDs and security group IDs if provided
        subnet_ids = args.subnet_ids.split(",") if args.subnet_ids else None
        security_group_ids = args.security_group_ids.split(",") if args.security_group_ids else None
        
        # Create Lambda Deployer
        deployer = LambdaDeployer(region_name=args.region)
        
        # Deploy Lambda function
        result = deployer.deploy(
            ecr_image_uri=args.ecr_image_uri,
            function_name=args.function_name,
            s3_bucket=args.s3_bucket,
            role_name=args.role_name,
            memory_size=args.memory_size,
            timeout=args.timeout,
            vpc_id=args.vpc_id,
            subnet_ids=subnet_ids,
            security_group_ids=security_group_ids,
            force_recreate_role=args.force_recreate_role
        )
        
        logger.info(f"Successfully deployed Lambda function: {result['function_arn']}")
        logger.info(f"Using IAM role: {result['role_arn']}")
        
        return 0
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Deployment failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
