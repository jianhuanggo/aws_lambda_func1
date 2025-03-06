"""
Unit tests for the S3 access manager.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

import boto3
import moto
from botocore.exceptions import ClientError

from lambda_deployer.s3.access_manager import S3AccessManager


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
def s3_client(aws_credentials):
    """S3 client fixture."""
    with moto.mock_aws():
        yield boto3.client('s3')


@pytest.fixture
def lambda_client(aws_credentials):
    """Lambda client fixture."""
    with moto.mock_aws():
        yield boto3.client('lambda')


@pytest.fixture
def s3_access_manager(aws_credentials):
    """S3 access manager fixture."""
    with moto.mock_aws():
        yield S3AccessManager()


def test_bucket_exists(s3_access_manager, s3_client):
    """Test checking if an S3 bucket exists."""
    bucket_name = "test-bucket"
    
    # Bucket should not exist initially
    assert not s3_access_manager._bucket_exists(bucket_name)
    
    # Create the bucket
    s3_client.create_bucket(Bucket=bucket_name)
    
    # Bucket should exist now
    assert s3_access_manager._bucket_exists(bucket_name)


@patch('boto3.client')
def test_update_lambda_environment(mock_boto3_client, aws_credentials):
    """Test updating Lambda function environment variables for S3 access."""
    # Mock the Lambda client
    mock_lambda_client = MagicMock()
    mock_boto3_client.return_value = mock_lambda_client
    
    # Mock the get_function_configuration response
    mock_lambda_client.get_function_configuration.return_value = {
        'Environment': {
            'Variables': {
                'EXISTING_VAR': 'existing_value'
            }
        }
    }
    
    # Mock the waiter
    mock_waiter = MagicMock()
    mock_lambda_client.get_waiter.return_value = mock_waiter
    
    # Create the S3 access manager
    s3_manager = S3AccessManager()
    
    # Test updating Lambda environment
    function_name = "test-function"
    s3_bucket = "test-bucket"
    
    s3_manager._update_lambda_environment(function_name, s3_bucket)
    
    # Verify get_function_configuration was called
    mock_lambda_client.get_function_configuration.assert_called_once_with(
        FunctionName=function_name
    )
    
    # Verify update_function_configuration was called with merged environment variables
    mock_lambda_client.update_function_configuration.assert_called_once_with(
        FunctionName=function_name,
        Environment={
            'Variables': {
                'EXISTING_VAR': 'existing_value',
                'S3_BUCKET': s3_bucket
            }
        }
    )
    
    # Verify the waiter was called
    mock_lambda_client.get_waiter.assert_called_once_with('function_updated')
    mock_waiter.wait.assert_called_once_with(FunctionName=function_name)


@patch('boto3.client')
def test_test_s3_access_success(mock_boto3_client, aws_credentials):
    """Test successful S3 access test."""
    # Mock the Lambda client
    mock_lambda_client = MagicMock()
    mock_boto3_client.return_value = mock_lambda_client
    
    # Mock the invoke response for successful access
    mock_lambda_client.invoke.return_value = {
        'StatusCode': 200,
        'Payload': b'{"success": true}'
    }
    
    # Create the S3 access manager
    s3_manager = S3AccessManager()
    
    # Test S3 access
    function_name = "test-function"
    s3_bucket = "test-bucket"
    
    result = s3_manager._test_s3_access(function_name, s3_bucket)
    
    # Verify invoke was called with the correct payload
    mock_lambda_client.invoke.assert_called_once()
    call_args = mock_lambda_client.invoke.call_args[1]
    assert call_args['FunctionName'] == function_name
    assert call_args['InvocationType'] == 'RequestResponse'
    
    # Verify the result is True
    assert result is True


@patch('boto3.client')
def test_test_s3_access_failure(mock_boto3_client, aws_credentials):
    """Test failed S3 access test."""
    # Mock the Lambda client
    mock_lambda_client = MagicMock()
    mock_boto3_client.return_value = mock_lambda_client
    
    # Mock the invoke response for failed access
    mock_lambda_client.invoke.return_value = {
        'StatusCode': 400,
        'Payload': b'{"success": false, "error": "Access denied"}'
    }
    
    # Create the S3 access manager
    s3_manager = S3AccessManager()
    
    # Test S3 access
    function_name = "test-function"
    s3_bucket = "test-bucket"
    
    result = s3_manager._test_s3_access(function_name, s3_bucket)
    
    # Verify invoke was called with the correct payload
    mock_lambda_client.invoke.assert_called_once()
    call_args = mock_lambda_client.invoke.call_args[1]
    assert call_args['FunctionName'] == function_name
    assert call_args['InvocationType'] == 'RequestResponse'
    
    # Verify the result is False
    assert result is False


@patch('lambda_deployer.s3.access_manager.S3AccessManager._bucket_exists')
@patch('lambda_deployer.s3.access_manager.S3AccessManager._update_lambda_environment')
def test_configure_s3_access_success(mock_update_env, mock_bucket_exists, aws_credentials):
    """Test successful S3 access configuration."""
    # Mock bucket_exists to return True
    mock_bucket_exists.return_value = True
    
    # Create the S3 access manager
    s3_manager = S3AccessManager()
    
    # Configure S3 access
    function_name = "test-function"
    s3_bucket = "test-bucket"
    
    result = s3_manager.configure_s3_access(function_name, s3_bucket)
    
    # Verify bucket_exists was called
    mock_bucket_exists.assert_called_once_with(s3_bucket)
    
    # Verify update_lambda_environment was called
    mock_update_env.assert_called_once_with(function_name, s3_bucket)
    
    # Verify the result is True
    assert result is True


@patch('lambda_deployer.s3.access_manager.S3AccessManager._bucket_exists')
def test_configure_s3_access_bucket_not_exists(mock_bucket_exists, aws_credentials):
    """Test S3 access configuration with non-existent bucket."""
    # Mock bucket_exists to return False
    mock_bucket_exists.return_value = False
    
    # Create the S3 access manager
    s3_manager = S3AccessManager()
    
    # Configure S3 access
    function_name = "test-function"
    s3_bucket = "test-bucket"
    
    # Should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        s3_manager.configure_s3_access(function_name, s3_bucket)
    
    # Verify bucket_exists was called
    mock_bucket_exists.assert_called_once_with(s3_bucket)
    
    # Verify the error message
    assert f"S3 bucket {s3_bucket} does not exist or is not accessible" in str(excinfo.value)
