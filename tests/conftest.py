"""
Pytest configuration file for Lambda Deployer tests.
"""
import os
import pytest
from unittest.mock import patch

import boto3
import moto


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
def lambda_client(aws_credentials):
    """Lambda client fixture."""
    with moto.mock_aws():
        yield boto3.client('lambda')


@pytest.fixture
def s3_client(aws_credentials):
    """S3 client fixture."""
    with moto.mock_aws():
        yield boto3.client('s3')


@pytest.fixture
def ec2_client(aws_credentials):
    """EC2 client fixture."""
    with moto.mock_aws():
        yield boto3.client('ec2')


@pytest.fixture
def sts_client(aws_credentials):
    """STS client fixture."""
    with moto.mock_aws():
        yield boto3.client('sts')
