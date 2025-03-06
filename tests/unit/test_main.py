"""
Unit tests for the main Lambda Deployer class.
"""
import pytest
from unittest.mock import patch, MagicMock

from lambda_deployer.main import LambdaDeployer


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


@patch('lambda_deployer.main.IAMRoleManager')
@patch('lambda_deployer.main.LambdaFunctionDeployer')
@patch('lambda_deployer.main.S3AccessManager')
@patch('lambda_deployer.main.VPCConfigurator')
def test_deploy_without_vpc(
    mock_vpc_configurator,
    mock_s3_manager,
    mock_lambda_deployer,
    mock_iam_manager,
    aws_credentials
):
    """Test deploying a Lambda function without VPC configuration."""
    # Mock the IAM role manager
    mock_iam_instance = MagicMock()
    mock_iam_instance.create_or_update_role.return_value = 'arn:aws:iam::123456789012:role/test-role'
    mock_iam_manager.return_value = mock_iam_instance
    
    # Mock the Lambda function deployer
    mock_lambda_instance = MagicMock()
    mock_lambda_instance.deploy_function.return_value = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    mock_lambda_deployer.return_value = mock_lambda_instance
    
    # Mock the S3 access manager
    mock_s3_instance = MagicMock()
    mock_s3_instance.configure_s3_access.return_value = True
    mock_s3_manager.return_value = mock_s3_instance
    
    # Create the Lambda Deployer
    deployer = LambdaDeployer()
    
    # Deploy a Lambda function
    result = deployer.deploy(
        ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
        function_name='test-function',
        s3_bucket='test-bucket',
        role_name='test-role',
        memory_size=256,
        timeout=60
    )
    
    # Verify the IAM role was created
    mock_iam_instance.create_or_update_role.assert_called_once_with(
        role_name='test-role',
        s3_bucket='test-bucket',
        force_recreate=False
    )
    
    # Verify the Lambda function was deployed
    mock_lambda_instance.deploy_function.assert_called_once_with(
        function_name='test-function',
        ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
        role_arn='arn:aws:iam::123456789012:role/test-role',
        memory_size=256,
        timeout=60,
        vpc_config=None
    )
    
    # Verify S3 access was configured
    mock_s3_instance.configure_s3_access.assert_called_once_with(
        function_name='test-function',
        s3_bucket='test-bucket'
    )
    
    # Verify the VPC configurator was not used
    mock_vpc_configurator.return_value.create_vpc_config.assert_not_called()
    
    # Verify the result
    assert result == {
        'function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
        'role_arn': 'arn:aws:iam::123456789012:role/test-role'
    }


@patch('lambda_deployer.main.IAMRoleManager')
@patch('lambda_deployer.main.LambdaFunctionDeployer')
@patch('lambda_deployer.main.S3AccessManager')
@patch('lambda_deployer.main.VPCConfigurator')
def test_deploy_with_vpc(
    mock_vpc_configurator,
    mock_s3_manager,
    mock_lambda_deployer,
    mock_iam_manager,
    aws_credentials
):
    """Test deploying a Lambda function with VPC configuration."""
    # Mock the IAM role manager
    mock_iam_instance = MagicMock()
    mock_iam_instance.create_or_update_role.return_value = 'arn:aws:iam::123456789012:role/test-role'
    mock_iam_manager.return_value = mock_iam_instance
    
    # Mock the Lambda function deployer
    mock_lambda_instance = MagicMock()
    mock_lambda_instance.deploy_function.return_value = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    mock_lambda_deployer.return_value = mock_lambda_instance
    
    # Mock the S3 access manager
    mock_s3_instance = MagicMock()
    mock_s3_instance.configure_s3_access.return_value = True
    mock_s3_manager.return_value = mock_s3_instance
    
    # Mock the VPC configurator
    mock_vpc_instance = MagicMock()
    mock_vpc_instance.create_vpc_config.return_value = {
        'SubnetIds': ['subnet-12345', 'subnet-67890'],
        'SecurityGroupIds': ['sg-12345']
    }
    mock_vpc_configurator.return_value = mock_vpc_instance
    
    # Create the Lambda Deployer
    deployer = LambdaDeployer()
    
    # Deploy a Lambda function with VPC configuration
    result = deployer.deploy(
        ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
        function_name='test-function',
        s3_bucket='test-bucket',
        role_name='test-role',
        memory_size=256,
        timeout=60,
        vpc_id='vpc-12345',
        subnet_ids=['subnet-12345', 'subnet-67890'],
        security_group_ids=['sg-12345']
    )
    
    # Verify the VPC configuration was created
    mock_vpc_instance.create_vpc_config.assert_called_once_with(
        vpc_id='vpc-12345',
        subnet_ids=['subnet-12345', 'subnet-67890'],
        security_group_ids=['sg-12345']
    )
    
    # Verify the IAM role was created
    mock_iam_instance.create_or_update_role.assert_called_once_with(
        role_name='test-role',
        s3_bucket='test-bucket',
        force_recreate=False
    )
    
    # Verify the Lambda function was deployed with VPC configuration
    mock_lambda_instance.deploy_function.assert_called_once_with(
        function_name='test-function',
        ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
        role_arn='arn:aws:iam::123456789012:role/test-role',
        memory_size=256,
        timeout=60,
        vpc_config={
            'SubnetIds': ['subnet-12345', 'subnet-67890'],
            'SecurityGroupIds': ['sg-12345']
        }
    )
    
    # Verify S3 access was configured
    mock_s3_instance.configure_s3_access.assert_called_once_with(
        function_name='test-function',
        s3_bucket='test-bucket'
    )
    
    # Verify the result
    assert result == {
        'function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
        'role_arn': 'arn:aws:iam::123456789012:role/test-role'
    }


@patch('lambda_deployer.main.IAMRoleManager')
@patch('lambda_deployer.main.LambdaFunctionDeployer')
@patch('lambda_deployer.main.S3AccessManager')
@patch('lambda_deployer.main.VPCConfigurator')
def test_deploy_with_default_role_name(
    mock_vpc_configurator,
    mock_s3_manager,
    mock_lambda_deployer,
    mock_iam_manager,
    aws_credentials
):
    """Test deploying a Lambda function with default role name."""
    # Mock the IAM role manager
    mock_iam_instance = MagicMock()
    mock_iam_instance.create_or_update_role.return_value = 'arn:aws:iam::123456789012:role/lambda-test-function-role'
    mock_iam_manager.return_value = mock_iam_instance
    
    # Mock the Lambda function deployer
    mock_lambda_instance = MagicMock()
    mock_lambda_instance.deploy_function.return_value = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    mock_lambda_deployer.return_value = mock_lambda_instance
    
    # Mock the S3 access manager
    mock_s3_instance = MagicMock()
    mock_s3_instance.configure_s3_access.return_value = True
    mock_s3_manager.return_value = mock_s3_instance
    
    # Create the Lambda Deployer
    deployer = LambdaDeployer()
    
    # Deploy a Lambda function without specifying a role name
    result = deployer.deploy(
        ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
        function_name='test-function',
        s3_bucket='test-bucket',
        memory_size=256,
        timeout=60
    )
    
    # Verify the IAM role was created with the default name
    mock_iam_instance.create_or_update_role.assert_called_once_with(
        role_name='lambda-test-function-role',
        s3_bucket='test-bucket',
        force_recreate=False
    )
    
    # Verify the Lambda function was deployed
    mock_lambda_instance.deploy_function.assert_called_once_with(
        function_name='test-function',
        ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
        role_arn='arn:aws:iam::123456789012:role/lambda-test-function-role',
        memory_size=256,
        timeout=60,
        vpc_config=None
    )
    
    # Verify S3 access was configured
    mock_s3_instance.configure_s3_access.assert_called_once_with(
        function_name='test-function',
        s3_bucket='test-bucket'
    )
    
    # Verify the result
    assert result == {
        'function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
        'role_arn': 'arn:aws:iam::123456789012:role/lambda-test-function-role'
    }


@patch('lambda_deployer.main.IAMRoleManager')
@patch('lambda_deployer.main.LambdaFunctionDeployer')
@patch('lambda_deployer.main.S3AccessManager')
@patch('lambda_deployer.main.VPCConfigurator')
def test_deploy_force_recreate_role(
    mock_vpc_configurator,
    mock_s3_manager,
    mock_lambda_deployer,
    mock_iam_manager,
    aws_credentials
):
    """Test deploying a Lambda function with force recreation of IAM role."""
    # Mock the IAM role manager
    mock_iam_instance = MagicMock()
    mock_iam_instance.create_or_update_role.return_value = 'arn:aws:iam::123456789012:role/test-role'
    mock_iam_manager.return_value = mock_iam_instance
    
    # Mock the Lambda function deployer
    mock_lambda_instance = MagicMock()
    mock_lambda_instance.deploy_function.return_value = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    mock_lambda_deployer.return_value = mock_lambda_instance
    
    # Mock the S3 access manager
    mock_s3_instance = MagicMock()
    mock_s3_instance.configure_s3_access.return_value = True
    mock_s3_manager.return_value = mock_s3_instance
    
    # Create the Lambda Deployer
    deployer = LambdaDeployer()
    
    # Deploy a Lambda function with force recreation of IAM role
    result = deployer.deploy(
        ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
        function_name='test-function',
        s3_bucket='test-bucket',
        role_name='test-role',
        memory_size=256,
        timeout=60,
        force_recreate_role=True
    )
    
    # Verify the IAM role was created with force_recreate=True
    mock_iam_instance.create_or_update_role.assert_called_once_with(
        role_name='test-role',
        s3_bucket='test-bucket',
        force_recreate=True
    )
    
    # Verify the Lambda function was deployed
    mock_lambda_instance.deploy_function.assert_called_once_with(
        function_name='test-function',
        ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
        role_arn='arn:aws:iam::123456789012:role/test-role',
        memory_size=256,
        timeout=60,
        vpc_config=None
    )
    
    # Verify S3 access was configured
    mock_s3_instance.configure_s3_access.assert_called_once_with(
        function_name='test-function',
        s3_bucket='test-bucket'
    )
    
    # Verify the result
    assert result == {
        'function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
        'role_arn': 'arn:aws:iam::123456789012:role/test-role'
    }


@patch('lambda_deployer.main.IAMRoleManager')
@patch('lambda_deployer.main.LambdaFunctionDeployer')
@patch('lambda_deployer.main.S3AccessManager')
@patch('lambda_deployer.main.VPCConfigurator')
def test_deploy_validation_error(
    mock_vpc_configurator,
    mock_s3_manager,
    mock_lambda_deployer,
    mock_iam_manager,
    aws_credentials
):
    """Test deploying a Lambda function with validation error."""
    # Create the Lambda Deployer
    deployer = LambdaDeployer()
    
    # Test with missing ECR image URI
    with pytest.raises(ValueError) as excinfo:
        deployer.deploy(
            ecr_image_uri='',
            function_name='test-function',
            s3_bucket='test-bucket'
        )
    assert "ECR image URI is required" in str(excinfo.value)
    
    # Test with missing function name
    with pytest.raises(ValueError) as excinfo:
        deployer.deploy(
            ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
            function_name='',
            s3_bucket='test-bucket'
        )
    assert "Function name is required" in str(excinfo.value)
    
    # Test with missing S3 bucket
    with pytest.raises(ValueError) as excinfo:
        deployer.deploy(
            ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
            function_name='test-function',
            s3_bucket=''
        )
    assert "S3 bucket name is required" in str(excinfo.value)
    
    # Test with VPC ID but no subnet IDs
    with pytest.raises(ValueError) as excinfo:
        deployer.deploy(
            ecr_image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:latest',
            function_name='test-function',
            s3_bucket='test-bucket',
            vpc_id='vpc-12345'
        )
    assert "Subnet IDs must be provided when using VPC configuration" in str(excinfo.value)
