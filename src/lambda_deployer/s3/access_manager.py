"""
S3 access manager for Lambda functions.
Handles configuration of S3 bucket access for Lambda functions.
"""
import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3AccessManager:
    """
    Manages S3 bucket access for Lambda functions.
    
    This class handles:
    - Verifying S3 bucket existence
    - Configuring Lambda functions with environment variables for S3 access
    - Testing S3 bucket access permissions
    """
    
    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize the S3 access manager.
        
        Args:
            region_name: AWS region name. If not provided, uses the default region.
        """
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.lambda_client = boto3.client('lambda', region_name=region_name)
    
    def _bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if an S3 bucket exists and is accessible.
        
        Args:
            bucket_name: Name of the S3 bucket to check
            
        Returns:
            True if the bucket exists and is accessible, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                logger.warning(f"S3 bucket {bucket_name} does not exist")
                return False
            elif error_code == '403':
                logger.warning(f"Access to S3 bucket {bucket_name} is forbidden")
                return False
            else:
                logger.error(f"Error checking S3 bucket {bucket_name}: {e}")
                raise
    
    def _update_lambda_environment(self, function_name: str, s3_bucket: str) -> None:
        """
        Update Lambda function environment variables for S3 access.
        
        Args:
            function_name: Name of the Lambda function
            s3_bucket: Name of the S3 bucket to access
        """
        try:
            # Get current environment variables
            response = self.lambda_client.get_function_configuration(
                FunctionName=function_name
            )
            
            # Update environment variables
            current_env = response.get('Environment', {}).get('Variables', {})
            updated_env = current_env.copy()
            updated_env['S3_BUCKET'] = s3_bucket
            
            # Update Lambda function configuration
            self.lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={
                    'Variables': updated_env
                }
            )
            
            logger.info(f"Updated Lambda function {function_name} environment with S3 bucket {s3_bucket}")
            
            # Wait for function to be updated
            waiter = self.lambda_client.get_waiter('function_updated')
            waiter.wait(FunctionName=function_name)
            
        except ClientError as e:
            logger.error(f"Error updating Lambda function {function_name} environment: {e}")
            raise
    
    def _test_s3_access(self, function_name: str, s3_bucket: str) -> bool:
        """
        Test if the Lambda function has access to the S3 bucket.
        
        Args:
            function_name: Name of the Lambda function
            s3_bucket: Name of the S3 bucket to test access to
            
        Returns:
            True if the Lambda function has access to the S3 bucket, False otherwise
        """
        try:
            # Create a test payload
            test_payload = {
                'operation': 'test_s3_access',
                's3_bucket': s3_bucket
            }
            
            # Invoke the Lambda function
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=bytes(str(test_payload), 'utf-8')
            )
            
            # Check the response
            status_code = response.get('StatusCode')
            if status_code == 200:
                logger.info(f"Lambda function {function_name} has access to S3 bucket {s3_bucket}")
                return True
            else:
                logger.warning(f"Lambda function {function_name} does not have access to S3 bucket {s3_bucket}")
                return False
            
        except ClientError as e:
            logger.error(f"Error testing S3 access for Lambda function {function_name}: {e}")
            return False
    
    def configure_s3_access(self, function_name: str, s3_bucket: str) -> bool:
        """
        Configure S3 bucket access for a Lambda function.
        
        Args:
            function_name: Name of the Lambda function
            s3_bucket: Name of the S3 bucket to configure access to
            
        Returns:
            True if S3 access was successfully configured, False otherwise
        """
        # Check if the S3 bucket exists
        if not self._bucket_exists(s3_bucket):
            logger.error(f"S3 bucket {s3_bucket} does not exist or is not accessible")
            raise ValueError(f"S3 bucket {s3_bucket} does not exist or is not accessible")
        
        # Update Lambda function environment variables
        self._update_lambda_environment(function_name, s3_bucket)
        
        logger.info(f"Successfully configured S3 access for Lambda function {function_name} to bucket {s3_bucket}")
        return True
