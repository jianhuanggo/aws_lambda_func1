"""
Unit tests for the Lambda function deployer.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

import boto3
import moto
from botocore.exceptions import ClientError

from lambda_deployer.lambda_func.function_deployer import LambdaFunctionDeployer


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
def lambda_client(aws_credentials):
    """Lambda client fixture."""
    with moto.mock_aws():
        yield boto3.client('lambda')


@pytest.fixture
def iam_client(aws_credentials):
    """IAM client fixture."""
    with moto.mock_aws():
        yield boto3.client('iam')


@pytest.fixture
def lambda_function_deployer(aws_credentials):
    """Lambda function deployer fixture."""
    with moto.mock_aws():
        yield LambdaFunctionDeployer()


@pytest.fixture
def lambda_role(iam_client):
    """Create a Lambda execution role."""
    role_name = "lambda-test-role"
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy)
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
    
    return response['Role']['Arn']


def test_function_exists(lambda_function_deployer, lambda_client, lambda_role):
    """Test checking if a Lambda function exists."""
    function_name = "test-function"
    
    # Function should not exist initially
    assert not lambda_function_deployer._function_exists(function_name)
    
    # Create a function
    lambda_client.create_function(
        FunctionName=function_name,
        Runtime='python3.9',
        Role=lambda_role,
        Handler='index.handler',
        Code={'ZipFile': b'def handler(event, context): return "Hello, World!"'},
        Description='Test function',
        Timeout=30,
        MemorySize=128,
        Publish=True
    )
    
    # Function should exist now
    assert lambda_function_deployer._function_exists(function_name)


@patch('boto3.client')
def test_create_function(mock_boto3_client, aws_credentials):
    """Test creating a Lambda function."""
    # Mock the Lambda client
    mock_lambda_client = MagicMock()
    mock_boto3_client.return_value = mock_lambda_client
    
    # Mock the create_function response
    mock_lambda_client.create_function.return_value = {
        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    }
    
    # Mock the waiter
    mock_waiter = MagicMock()
    mock_lambda_client.get_waiter.return_value = mock_waiter
    
    # Create the function deployer
    deployer = LambdaFunctionDeployer()
    
    # Test creating a function
    function_name = "test-function"
    ecr_image_uri = "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest"
    role_arn = "arn:aws:iam::123456789012:role/lambda-test-role"
    
    function_arn = deployer._create_function(
        function_name=function_name,
        ecr_image_uri=ecr_image_uri,
        role_arn=role_arn,
        memory_size=256,
        timeout=60
    )
    
    # Verify the function was created
    mock_lambda_client.create_function.assert_called_once_with(
        FunctionName=function_name,
        Role=role_arn,
        PackageType='Image',
        Code={'ImageUri': ecr_image_uri},
        MemorySize=256,
        Timeout=60
    )
    
    # Verify the waiter was called
    mock_lambda_client.get_waiter.assert_called_once_with('function_active')
    mock_waiter.wait.assert_called_once_with(FunctionName=function_name)
    
    # Verify the function ARN was returned
    assert function_arn == 'arn:aws:lambda:us-east-1:123456789012:function:test-function'


@patch('boto3.client')
def test_create_function_with_vpc(mock_boto3_client, aws_credentials):
    """Test creating a Lambda function with VPC configuration."""
    # Mock the Lambda client
    mock_lambda_client = MagicMock()
    mock_boto3_client.return_value = mock_lambda_client
    
    # Mock the create_function response
    mock_lambda_client.create_function.return_value = {
        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    }
    
    # Mock the waiter
    mock_waiter = MagicMock()
    mock_lambda_client.get_waiter.return_value = mock_waiter
    
    # Create the function deployer
    deployer = LambdaFunctionDeployer()
    
    # Test creating a function with VPC configuration
    function_name = "test-function"
    ecr_image_uri = "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest"
    role_arn = "arn:aws:iam::123456789012:role/lambda-test-role"
    vpc_config = {
        'SubnetIds': ['subnet-12345', 'subnet-67890'],
        'SecurityGroupIds': ['sg-12345']
    }
    
    function_arn = deployer._create_function(
        function_name=function_name,
        ecr_image_uri=ecr_image_uri,
        role_arn=role_arn,
        memory_size=256,
        timeout=60,
        vpc_config=vpc_config
    )
    
    # Verify the function was created with VPC configuration
    mock_lambda_client.create_function.assert_called_once_with(
        FunctionName=function_name,
        Role=role_arn,
        PackageType='Image',
        Code={'ImageUri': ecr_image_uri},
        MemorySize=256,
        Timeout=60,
        VpcConfig=vpc_config
    )
    
    # Verify the waiter was called
    mock_lambda_client.get_waiter.assert_called_once_with('function_active')
    mock_waiter.wait.assert_called_once_with(FunctionName=function_name)
    
    # Verify the function ARN was returned
    assert function_arn == 'arn:aws:lambda:us-east-1:123456789012:function:test-function'


@patch('boto3.client')
def test_update_function_code(mock_boto3_client, aws_credentials):
    """Test updating a Lambda function's code."""
    # Mock the Lambda client
    mock_lambda_client = MagicMock()
    mock_boto3_client.return_value = mock_lambda_client
    
    # Mock the update_function_code response
    mock_lambda_client.update_function_code.return_value = {
        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    }
    
    # Mock the waiter
    mock_waiter = MagicMock()
    mock_lambda_client.get_waiter.return_value = mock_waiter
    
    # Create the function deployer
    deployer = LambdaFunctionDeployer()
    
    # Test updating a function's code
    function_name = "test-function"
    ecr_image_uri = "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest"
    
    function_arn = deployer._update_function_code(
        function_name=function_name,
        ecr_image_uri=ecr_image_uri
    )
    
    # Verify the function code was updated
    mock_lambda_client.update_function_code.assert_called_once_with(
        FunctionName=function_name,
        ImageUri=ecr_image_uri
    )
    
    # Verify the waiter was called
    mock_lambda_client.get_waiter.assert_called_once_with('function_updated')
    mock_waiter.wait.assert_called_once_with(FunctionName=function_name)
    
    # Verify the function ARN was returned
    assert function_arn == 'arn:aws:lambda:us-east-1:123456789012:function:test-function'


@patch('boto3.client')
def test_update_function_configuration(mock_boto3_client, aws_credentials):
    """Test updating a Lambda function's configuration."""
    # Mock the Lambda client
    mock_lambda_client = MagicMock()
    mock_boto3_client.return_value = mock_lambda_client
    
    # Mock the update_function_configuration response
    mock_lambda_client.update_function_configuration.return_value = {
        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    }
    
    # Mock the waiter
    mock_waiter = MagicMock()
    mock_lambda_client.get_waiter.return_value = mock_waiter
    
    # Create the function deployer
    deployer = LambdaFunctionDeployer()
    
    # Test updating a function's configuration
    function_name = "test-function"
    role_arn = "arn:aws:iam::123456789012:role/lambda-test-role"
    vpc_config = {
        'SubnetIds': ['subnet-12345', 'subnet-67890'],
        'SecurityGroupIds': ['sg-12345']
    }
    
    function_arn = deployer._update_function_configuration(
        function_name=function_name,
        role_arn=role_arn,
        memory_size=512,
        timeout=120,
        vpc_config=vpc_config
    )
    
    # Verify the function configuration was updated
    mock_lambda_client.update_function_configuration.assert_called_once_with(
        FunctionName=function_name,
        Role=role_arn,
        MemorySize=512,
        Timeout=120,
        VpcConfig=vpc_config
    )
    
    # Verify the waiter was called
    mock_lambda_client.get_waiter.assert_called_once_with('function_updated')
    mock_waiter.wait.assert_called_once_with(FunctionName=function_name)
    
    # Verify the function ARN was returned
    assert function_arn == 'arn:aws:lambda:us-east-1:123456789012:function:test-function'


@patch('lambda_deployer.lambda_func.function_deployer.LambdaFunctionDeployer._function_exists')
@patch('lambda_deployer.lambda_func.function_deployer.LambdaFunctionDeployer._create_function')
def test_deploy_function_new(mock_create_function, mock_function_exists, aws_credentials):
    """Test deploying a new Lambda function."""
    # Mock function_exists to return False (function doesn't exist)
    mock_function_exists.return_value = False
    
    # Mock create_function to return a function ARN
    mock_create_function.return_value = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    
    # Create the function deployer
    deployer = LambdaFunctionDeployer()
    
    # Test deploying a new function
    function_name = "test-function"
    ecr_image_uri = "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest"
    role_arn = "arn:aws:iam::123456789012:role/lambda-test-role"
    
    function_arn = deployer.deploy_function(
        function_name=function_name,
        ecr_image_uri=ecr_image_uri,
        role_arn=role_arn,
        memory_size=256,
        timeout=60
    )
    
    # Verify function_exists was called
    mock_function_exists.assert_called_once_with(function_name)
    
    # Verify create_function was called
    mock_create_function.assert_called_once_with(
        function_name=function_name,
        ecr_image_uri=ecr_image_uri,
        role_arn=role_arn,
        memory_size=256,
        timeout=60,
        vpc_config=None
    )
    
    # Verify the function ARN was returned
    assert function_arn == 'arn:aws:lambda:us-east-1:123456789012:function:test-function'


@patch('lambda_deployer.lambda_func.function_deployer.LambdaFunctionDeployer._function_exists')
@patch('lambda_deployer.lambda_func.function_deployer.LambdaFunctionDeployer._update_function_code')
@patch('lambda_deployer.lambda_func.function_deployer.LambdaFunctionDeployer._update_function_configuration')
def test_deploy_function_existing(mock_update_config, mock_update_code, mock_function_exists, aws_credentials):
    """Test deploying an existing Lambda function."""
    # Mock function_exists to return True (function exists)
    mock_function_exists.return_value = True
    
    # Mock update_function_code to return a function ARN
    mock_update_code.return_value = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    
    # Mock update_function_configuration to return a function ARN
    mock_update_config.return_value = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    
    # Create the function deployer
    deployer = LambdaFunctionDeployer()
    
    # Test deploying an existing function
    function_name = "test-function"
    ecr_image_uri = "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest"
    role_arn = "arn:aws:iam::123456789012:role/lambda-test-role"
    vpc_config = {
        'SubnetIds': ['subnet-12345', 'subnet-67890'],
        'SecurityGroupIds': ['sg-12345']
    }
    
    function_arn = deployer.deploy_function(
        function_name=function_name,
        ecr_image_uri=ecr_image_uri,
        role_arn=role_arn,
        memory_size=512,
        timeout=120,
        vpc_config=vpc_config
    )
    
    # Verify function_exists was called
    mock_function_exists.assert_called_once_with(function_name)
    
    # Verify update_function_code was called
    mock_update_code.assert_called_once_with(
        function_name=function_name,
        ecr_image_uri=ecr_image_uri
    )
    
    # Verify update_function_configuration was called
    mock_update_config.assert_called_once_with(
        function_name=function_name,
        role_arn=role_arn,
        memory_size=512,
        timeout=120,
        vpc_config=vpc_config
    )
    
    # Verify the function ARN was returned
    assert function_arn == 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
