"""
Lambda function deployer module.
Handles deployment of ECR images to AWS Lambda functions.
"""
import logging
from typing import Dict, Optional, Union

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class LambdaFunctionDeployer:
    """
    Deploys ECR container images to AWS Lambda functions.
    
    This class handles:
    - Creating new Lambda functions from ECR images
    - Updating existing Lambda functions with new ECR images
    - Configuring Lambda function settings (memory, timeout, etc.)
    - Setting up VPC configuration if specified
    """
    
    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize the Lambda function deployer.
        
        Args:
            region_name: AWS region name. If not provided, uses the default region.
        """
        self.lambda_client = boto3.client('lambda', region_name=region_name)
    
    def _function_exists(self, function_name: str) -> bool:
        """
        Check if a Lambda function exists.
        
        Args:
            function_name: Name of the Lambda function to check
            
        Returns:
            True if the function exists, False otherwise
        """
        try:
            self.lambda_client.get_function(FunctionName=function_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise
    
    def _create_function(
        self,
        function_name: str,
        ecr_image_uri: str,
        role_arn: str,
        memory_size: int = 128,
        timeout: int = 30,
        vpc_config: Optional[Dict[str, Union[str, list]]] = None
    ) -> str:
        """
        Create a new Lambda function from an ECR image.
        
        Args:
            function_name: Name of the Lambda function
            ecr_image_uri: URI of the ECR image to deploy
            role_arn: ARN of the IAM role for the Lambda function
            memory_size: Memory size for the Lambda function in MB
            timeout: Timeout for the Lambda function in seconds
            vpc_config: VPC configuration for the Lambda function
            
        Returns:
            ARN of the created Lambda function
        """
        try:
            params = {
                'FunctionName': function_name,
                'Role': role_arn,
                'PackageType': 'Image',
                'Code': {
                    'ImageUri': ecr_image_uri
                },
                'MemorySize': memory_size,
                'Timeout': timeout,
            }
            
            if vpc_config:
                params['VpcConfig'] = vpc_config
            
            response = self.lambda_client.create_function(**params)
            
            function_arn = response['FunctionArn']
            logger.info(f"Created Lambda function: {function_arn}")
            
            # Wait for function to be active
            waiter = self.lambda_client.get_waiter('function_active')
            waiter.wait(FunctionName=function_name)
            
            return function_arn
        
        except ClientError as e:
            logger.error(f"Error creating Lambda function {function_name}: {e}")
            raise
    
    def _update_function_code(self, function_name: str, ecr_image_uri: str) -> str:
        """
        Update an existing Lambda function with a new ECR image.
        
        Args:
            function_name: Name of the Lambda function
            ecr_image_uri: URI of the ECR image to deploy
            
        Returns:
            ARN of the updated Lambda function
        """
        try:
            response = self.lambda_client.update_function_code(
                FunctionName=function_name,
                ImageUri=ecr_image_uri
            )
            
            function_arn = response['FunctionArn']
            logger.info(f"Updated Lambda function code: {function_arn}")
            
            # Wait for function to be updated
            waiter = self.lambda_client.get_waiter('function_updated')
            waiter.wait(FunctionName=function_name)
            
            return function_arn
        
        except ClientError as e:
            logger.error(f"Error updating Lambda function code for {function_name}: {e}")
            raise
    
    def _update_function_configuration(
        self,
        function_name: str,
        role_arn: str,
        memory_size: int = 128,
        timeout: int = 30,
        vpc_config: Optional[Dict[str, Union[str, list]]] = None
    ) -> str:
        """
        Update Lambda function configuration.
        
        Args:
            function_name: Name of the Lambda function
            role_arn: ARN of the IAM role for the Lambda function
            memory_size: Memory size for the Lambda function in MB
            timeout: Timeout for the Lambda function in seconds
            vpc_config: VPC configuration for the Lambda function
            
        Returns:
            ARN of the updated Lambda function
        """
        try:
            params = {
                'FunctionName': function_name,
                'Role': role_arn,
                'MemorySize': memory_size,
                'Timeout': timeout,
            }
            
            if vpc_config:
                params['VpcConfig'] = vpc_config
            
            response = self.lambda_client.update_function_configuration(**params)
            
            function_arn = response['FunctionArn']
            logger.info(f"Updated Lambda function configuration: {function_arn}")
            
            # Wait for function to be updated
            waiter = self.lambda_client.get_waiter('function_updated')
            waiter.wait(FunctionName=function_name)
            
            return function_arn
        
        except ClientError as e:
            logger.error(f"Error updating Lambda function configuration for {function_name}: {e}")
            raise
    
    def deploy_function(
        self,
        function_name: str,
        ecr_image_uri: str,
        role_arn: str,
        memory_size: int = 128,
        timeout: int = 30,
        vpc_config: Optional[Dict[str, Union[str, list]]] = None
    ) -> str:
        """
        Deploy an ECR image to a Lambda function.
        
        If the function doesn't exist, it will be created.
        If the function exists, it will be updated.
        
        Args:
            function_name: Name of the Lambda function
            ecr_image_uri: URI of the ECR image to deploy
            role_arn: ARN of the IAM role for the Lambda function
            memory_size: Memory size for the Lambda function in MB
            timeout: Timeout for the Lambda function in seconds
            vpc_config: VPC configuration for the Lambda function
            
        Returns:
            ARN of the deployed Lambda function
        """
        # Check if function exists
        function_exists = self._function_exists(function_name)
        
        if function_exists:
            logger.info(f"Lambda function {function_name} exists, updating it")
            
            # Update function code
            function_arn = self._update_function_code(
                function_name=function_name,
                ecr_image_uri=ecr_image_uri
            )
            
            # Update function configuration
            function_arn = self._update_function_configuration(
                function_name=function_name,
                role_arn=role_arn,
                memory_size=memory_size,
                timeout=timeout,
                vpc_config=vpc_config
            )
        else:
            logger.info(f"Lambda function {function_name} does not exist, creating it")
            
            # Create function
            function_arn = self._create_function(
                function_name=function_name,
                ecr_image_uri=ecr_image_uri,
                role_arn=role_arn,
                memory_size=memory_size,
                timeout=timeout,
                vpc_config=vpc_config
            )
        
        return function_arn
