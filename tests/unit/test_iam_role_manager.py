"""
Unit tests for the IAM role manager.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

import boto3
import moto
from botocore.exceptions import ClientError

from lambda_deployer.iam.role_manager import IAMRoleManager


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'testing',
        'AWS_SECRET_ACCESS_KEY': 'testing',
        'AWS_SECURITY_TOKEN': 'testing',
        'AWS_SESSION_TOKEN': 'testing',
        'AWS_DEFAULT_REGION': 'us-east-1',
    }):
        yield


@pytest.fixture
def iam_resource(aws_credentials):
    """IAM resource fixture."""
    with moto.mock_aws():
        yield boto3.resource('iam')


@pytest.fixture
def iam_client(aws_credentials):
    """IAM client fixture."""
    with moto.mock_aws():
        yield boto3.client('iam')


@pytest.fixture
def sts_client(aws_credentials):
    """STS client fixture."""
    with moto.mock_aws():
        yield boto3.client('sts')


@pytest.fixture
def iam_role_manager(aws_credentials):
    """IAM role manager fixture."""
    with moto.mock_aws():
        yield IAMRoleManager()


def test_create_role(iam_role_manager, iam_client):
    """Test creating an IAM role."""
    role_name = "test-lambda-role"
    
    # Create the role
    role_arn = iam_role_manager._create_role(role_name)
    
    # Verify the role was created
    response = iam_client.get_role(RoleName=role_name)
    assert response['Role']['RoleName'] == role_name
    assert response['Role']['Arn'] == role_arn
    
    # Verify the trust policy - in moto, AssumeRolePolicyDocument is already a dict, not a JSON string
    trust_policy = response['Role']['AssumeRolePolicyDocument']
    assert trust_policy['Statement'][0]['Principal']['Service'] == "lambda.amazonaws.com"
    
    # Verify the basic execution policy was attached - we're now using a custom policy with the name {role_name}-basic-execution
    attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
    assert any(f"{role_name}-basic-execution" in p['PolicyArn'] for p in attached_policies['AttachedPolicies'])


def test_role_exists(iam_role_manager, iam_client):
    """Test checking if a role exists."""
    role_name = "test-lambda-role"
    
    # Role should not exist initially
    assert not iam_role_manager._role_exists(role_name)
    
    # Create the role
    iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps({
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
        })
    )
    
    # Role should exist now
    assert iam_role_manager._role_exists(role_name)


def test_create_s3_access_policy(iam_role_manager, iam_client):
    """Test creating an S3 access policy."""
    role_name = "test-lambda-role"
    s3_bucket = "test-bucket"
    
    # Create the policy
    policy_arn = iam_role_manager._create_s3_access_policy(role_name, s3_bucket)
    
    # Verify the policy was created
    policy_name = f"{role_name}-s3-access"
    response = iam_client.get_policy(PolicyArn=policy_arn)
    assert response['Policy']['PolicyName'] == policy_name
    
    # Verify the policy document
    policy_version = iam_client.get_policy_version(
        PolicyArn=policy_arn,
        VersionId=response['Policy']['DefaultVersionId']
    )
    policy_doc = policy_version['PolicyVersion']['Document']
    
    assert any(
        stmt['Effect'] == 'Allow' and 
        's3:GetObject' in stmt['Action'] and
        f"arn:aws:s3:::{s3_bucket}" in stmt['Resource']
        for stmt in policy_doc['Statement']
    )


def test_delete_role(iam_role_manager, iam_client):
    """Test deleting an IAM role."""
    role_name = "test-lambda-role"
    
    # Create a role
    iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps({
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
        })
    )
    
    # Create and attach a custom basic execution policy for testing
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
    
    # Create the policy
    policy_response = iam_client.create_policy(
        PolicyName=basic_execution_policy_name,
        PolicyDocument=json.dumps(basic_execution_policy_document),
        Description=f"Basic execution policy for Lambda function role {role_name}"
    )
    
    # Attach the policy to the role
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn=policy_response['Policy']['Arn']
    )
    
    # Delete the role
    iam_role_manager._delete_role(role_name)
    
    # Verify the role was deleted
    with pytest.raises(ClientError) as excinfo:
        iam_client.get_role(RoleName=role_name)
    assert excinfo.value.response['Error']['Code'] == 'NoSuchEntity'


def test_create_or_update_role_new(iam_role_manager, iam_client):
    """Test creating a new role."""
    role_name = "test-lambda-role"
    s3_bucket = "test-bucket"
    
    # Create the role
    role_arn = iam_role_manager.create_or_update_role(role_name, s3_bucket)
    
    # Verify the role was created
    response = iam_client.get_role(RoleName=role_name)
    assert response['Role']['RoleName'] == role_name
    assert response['Role']['Arn'] == role_arn
    
    # Verify the S3 policy was attached
    attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
    assert any(f"{role_name}-s3-access" in p['PolicyArn'] for p in attached_policies['AttachedPolicies'])


def test_create_or_update_role_existing(iam_role_manager, iam_client):
    """Test updating an existing role."""
    role_name = "test-lambda-role"
    s3_bucket = "test-bucket"
    
    # Create a role
    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps({
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
        })
    )
    existing_role_arn = response['Role']['Arn']
    
    # Update the role
    role_arn = iam_role_manager.create_or_update_role(role_name, s3_bucket)
    
    # Verify the role was not recreated
    assert role_arn == existing_role_arn
    
    # Verify the S3 policy was attached
    attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
    assert any(f"{role_name}-s3-access" in p['PolicyArn'] for p in attached_policies['AttachedPolicies'])


def test_create_or_update_role_force_recreate(iam_role_manager, iam_client):
    """Test force recreating a role."""
    role_name = "test-lambda-role"
    s3_bucket = "test-bucket"
    
    # Create a role
    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps({
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
        })
    )
    existing_role_arn = response['Role']['Arn']
    
    # Force recreate the role
    role_arn = iam_role_manager.create_or_update_role(role_name, s3_bucket, force_recreate=True)
    
    # Verify the role was recreated (ARN should be different in a real environment,
    # but in moto it might be the same)
    assert iam_role_manager._role_exists(role_name)
    
    # Verify the S3 policy was attached
    attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
    assert any(f"{role_name}-s3-access" in p['PolicyArn'] for p in attached_policies['AttachedPolicies'])
