"""
IAM role manager for Lambda functions.
Handles creation, validation, and cleanup of IAM roles and policies.
"""
import json
import logging
import time
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class IAMRoleManager:
    """
    Manages IAM roles and policies for Lambda functions.
    
    This class handles:
    - Creating IAM roles for Lambda functions
    - Attaching policies for S3 access
    - Checking for existing roles and policies
    - Removing conflicting roles and policies
    """
    
    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize the IAM role manager.
        
        Args:
            region_name: AWS region name. If not provided, uses the default region.
        """
        self.iam_client = boto3.client('iam', region_name=region_name)
        self.lambda_execution_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
    
    def _create_s3_access_policy(self, role_name: str, s3_bucket: str) -> str:
        """
        Create an IAM policy for S3 access.
        
        Args:
            role_name: Name of the IAM role
            s3_bucket: Name of the S3 bucket to grant access to
            
        Returns:
            ARN of the created policy
        """
        policy_name = f"{role_name}-s3-access"
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:ListBucket",
                        "s3:DeleteObject"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{s3_bucket}",
                        f"arn:aws:s3:::{s3_bucket}/*"
                    ]
                }
            ]
        }
        
        try:
            # Check if policy already exists
            try:
                response = self.iam_client.get_policy(
                    PolicyArn=f"arn:aws:iam::{self._get_account_id()}:policy/{policy_name}"
                )
                logger.info(f"Policy {policy_name} already exists, deleting it first")
                self._delete_policy(response['Policy']['Arn'])
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise
            
            # Create the policy
            response = self.iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document),
                Description=f"S3 access policy for Lambda function role {role_name}"
            )
            policy_arn = response['Policy']['Arn']
            logger.info(f"Created S3 access policy: {policy_arn}")
            return policy_arn
            
        except ClientError as e:
            logger.error(f"Error creating S3 access policy: {e}")
            raise
    
    def _get_account_id(self) -> str:
        """
        Get the AWS account ID.
        
        Returns:
            AWS account ID
        """
        sts_client = boto3.client('sts')
        return sts_client.get_caller_identity()['Account']
    
    def _delete_policy(self, policy_arn: str) -> None:
        """
        Delete an IAM policy.
        
        Args:
            policy_arn: ARN of the policy to delete
        """
        try:
            # Detach the policy from all entities first
            self._detach_policy_from_all_entities(policy_arn)
            
            # Delete the policy
            self.iam_client.delete_policy(PolicyArn=policy_arn)
            logger.info(f"Deleted policy: {policy_arn}")
        except ClientError as e:
            logger.error(f"Error deleting policy {policy_arn}: {e}")
            raise
    
    def _detach_policy_from_all_entities(self, policy_arn: str) -> None:
        """
        Detach a policy from all attached entities.
        
        Args:
            policy_arn: ARN of the policy to detach
        """
        try:
            # Detach from roles
            response = self.iam_client.list_entities_for_policy(
                PolicyArn=policy_arn,
                EntityFilter='Role'
            )
            
            for role in response.get('PolicyRoles', []):
                self.iam_client.detach_role_policy(
                    RoleName=role['RoleName'],
                    PolicyArn=policy_arn
                )
                logger.info(f"Detached policy {policy_arn} from role {role['RoleName']}")
            
            # Handle pagination if needed
            while response.get('IsTruncated', False):
                response = self.iam_client.list_entities_for_policy(
                    PolicyArn=policy_arn,
                    EntityFilter='Role',
                    Marker=response['Marker']
                )
                
                for role in response.get('PolicyRoles', []):
                    self.iam_client.detach_role_policy(
                        RoleName=role['RoleName'],
                        PolicyArn=policy_arn
                    )
                    logger.info(f"Detached policy {policy_arn} from role {role['RoleName']}")
        
        except ClientError as e:
            logger.error(f"Error detaching policy {policy_arn} from entities: {e}")
            raise
    
    def _delete_role(self, role_name: str) -> None:
        """
        Delete an IAM role.
        
        Args:
            role_name: Name of the role to delete
        """
        try:
            # Detach all policies from the role
            self._detach_all_policies_from_role(role_name)
            
            # Delete the role
            self.iam_client.delete_role(RoleName=role_name)
            logger.info(f"Deleted role: {role_name}")
        except ClientError as e:
            logger.error(f"Error deleting role {role_name}: {e}")
            raise
    
    def _detach_all_policies_from_role(self, role_name: str) -> None:
        """
        Detach all policies from a role.
        
        Args:
            role_name: Name of the role
        """
        try:
            # List all attached managed policies
            response = self.iam_client.list_attached_role_policies(RoleName=role_name)
            
            for policy in response.get('AttachedPolicies', []):
                self.iam_client.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy['PolicyArn']
                )
                logger.info(f"Detached policy {policy['PolicyArn']} from role {role_name}")
            
            # Handle pagination if needed
            while response.get('IsTruncated', False):
                response = self.iam_client.list_attached_role_policies(
                    RoleName=role_name,
                    Marker=response['Marker']
                )
                
                for policy in response.get('AttachedPolicies', []):
                    self.iam_client.detach_role_policy(
                        RoleName=role_name,
                        PolicyArn=policy['PolicyArn']
                    )
                    logger.info(f"Detached policy {policy['PolicyArn']} from role {role_name}")
            
            # List and delete inline policies
            response = self.iam_client.list_role_policies(RoleName=role_name)
            
            for policy_name in response.get('PolicyNames', []):
                self.iam_client.delete_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                logger.info(f"Deleted inline policy {policy_name} from role {role_name}")
            
            # Handle pagination if needed
            while response.get('IsTruncated', False):
                response = self.iam_client.list_role_policies(
                    RoleName=role_name,
                    Marker=response['Marker']
                )
                
                for policy_name in response.get('PolicyNames', []):
                    self.iam_client.delete_role_policy(
                        RoleName=role_name,
                        PolicyName=policy_name
                    )
                    logger.info(f"Deleted inline policy {policy_name} from role {role_name}")
        
        except ClientError as e:
            logger.error(f"Error detaching policies from role {role_name}: {e}")
            raise
    
    def _role_exists(self, role_name: str) -> bool:
        """
        Check if an IAM role exists.
        
        Args:
            role_name: Name of the role to check
            
        Returns:
            True if the role exists, False otherwise
        """
        try:
            self.iam_client.get_role(RoleName=role_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                return False
            raise
    
    def _create_role(self, role_name: str) -> str:
        """
        Create an IAM role for Lambda execution.
        
        Args:
            role_name: Name of the role to create
            
        Returns:
            ARN of the created role
        """
        try:
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(self.lambda_execution_trust_policy),
                Description=f"Role for Lambda function execution with S3 access"
            )
            
            role_arn = response['Role']['Arn']
            logger.info(f"Created IAM role: {role_arn}")
            
            # Create and attach basic Lambda execution policy
            # For testing purposes, we create our own basic execution policy
            # instead of using the AWS managed policy which may not be available in test environments
            basic_execution_policy_name = f"{role_name}-basic-execution"
            basic_execution_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ],
                        "Resource": "arn:aws:logs:*:*:*"
                    }
                ]
            }
            
            try:
                response = self.iam_client.create_policy(
                    PolicyName=basic_execution_policy_name,
                    PolicyDocument=json.dumps(basic_execution_policy_document),
                    Description=f"Basic execution policy for Lambda function role {role_name}"
                )
                basic_policy_arn = response['Policy']['Arn']
                
                self.iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=basic_policy_arn
                )
                logger.info(f"Created and attached basic execution policy {basic_policy_arn} to role {role_name}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityAlreadyExists':
                    # Policy already exists, get its ARN and attach it
                    account_id = self._get_account_id()
                    basic_policy_arn = f"arn:aws:iam::{account_id}:policy/{basic_execution_policy_name}"
                    self.iam_client.attach_role_policy(
                        RoleName=role_name,
                        PolicyArn=basic_policy_arn
                    )
                    logger.info(f"Attached existing basic execution policy {basic_policy_arn} to role {role_name}")
                else:
                    raise
            
            # Wait for role to propagate
            logger.info(f"Waiting for role {role_name} to propagate...")
            time.sleep(5)
            
            return role_arn
        
        except ClientError as e:
            logger.error(f"Error creating role {role_name}: {e}")
            raise
    
    def create_or_update_role(self, role_name: str, s3_bucket: str, force_recreate: bool = False) -> str:
        """
        Create or update an IAM role for Lambda function with S3 access.
        
        Args:
            role_name: Name of the IAM role
            s3_bucket: Name of the S3 bucket to grant access to
            force_recreate: If True, delete and recreate the role even if it exists
            
        Returns:
            ARN of the created or updated role
        """
        # Check if role exists
        role_exists = self._role_exists(role_name)
        
        # Delete role if it exists and force_recreate is True
        if role_exists and force_recreate:
            logger.info(f"Role {role_name} exists and force_recreate is True, deleting it")
            self._delete_role(role_name)
            role_exists = False
        
        # Create role if it doesn't exist
        if not role_exists:
            role_arn = self._create_role(role_name)
        else:
            logger.info(f"Role {role_name} already exists, using it")
            response = self.iam_client.get_role(RoleName=role_name)
            role_arn = response['Role']['Arn']
        
        # Create and attach S3 access policy
        s3_policy_arn = self._create_s3_access_policy(role_name, s3_bucket)
        
        # Attach S3 access policy to role
        self.iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=s3_policy_arn
        )
        logger.info(f"Attached S3 access policy {s3_policy_arn} to role {role_name}")
        
        return role_arn
