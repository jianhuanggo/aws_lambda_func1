"""
Unit tests for the VPC configurator.
"""
import pytest
from unittest.mock import patch, MagicMock

import boto3
import moto
from botocore.exceptions import ClientError

from lambda_deployer.vpc.configurator import VPCConfigurator


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
def ec2_client(aws_credentials):
    """EC2 client fixture."""
    with moto.mock_aws():
        yield boto3.client('ec2')


@pytest.fixture
def vpc_configurator(aws_credentials):
    """VPC configurator fixture."""
    with moto.mock_aws():
        yield VPCConfigurator()


@pytest.fixture
def test_vpc(ec2_client):
    """Create a test VPC."""
    response = ec2_client.create_vpc(
        CidrBlock='10.0.0.0/16'
    )
    vpc_id = response['Vpc']['VpcId']
    
    # Add a name tag
    ec2_client.create_tags(
        Resources=[vpc_id],
        Tags=[
            {
                'Key': 'Name',
                'Value': 'test-vpc'
            }
        ]
    )
    
    return vpc_id


@pytest.fixture
def test_subnets(ec2_client, test_vpc):
    """Create test subnets in the VPC."""
    subnet_ids = []
    
    # Create two subnets in different AZs
    response = ec2_client.create_subnet(
        VpcId=test_vpc,
        CidrBlock='10.0.1.0/24',
        AvailabilityZone='us-east-1a'
    )
    subnet_id1 = response['Subnet']['SubnetId']
    subnet_ids.append(subnet_id1)
    
    # Add a name tag
    ec2_client.create_tags(
        Resources=[subnet_id1],
        Tags=[
            {
                'Key': 'Name',
                'Value': 'test-subnet-1'
            }
        ]
    )
    
    response = ec2_client.create_subnet(
        VpcId=test_vpc,
        CidrBlock='10.0.2.0/24',
        AvailabilityZone='us-east-1b'
    )
    subnet_id2 = response['Subnet']['SubnetId']
    subnet_ids.append(subnet_id2)
    
    # Add a name tag
    ec2_client.create_tags(
        Resources=[subnet_id2],
        Tags=[
            {
                'Key': 'Name',
                'Value': 'test-subnet-2'
            }
        ]
    )
    
    return subnet_ids


@pytest.fixture
def test_security_group(ec2_client, test_vpc):
    """Create a test security group in the VPC."""
    response = ec2_client.create_security_group(
        GroupName='test-sg',
        Description='Test security group',
        VpcId=test_vpc
    )
    sg_id = response['GroupId']
    
    # Add a name tag
    ec2_client.create_tags(
        Resources=[sg_id],
        Tags=[
            {
                'Key': 'Name',
                'Value': 'test-sg'
            }
        ]
    )
    
    return sg_id


def test_validate_vpc_exists(vpc_configurator, test_vpc):
    """Test validating a VPC that exists."""
    # VPC should exist
    assert vpc_configurator._validate_vpc(test_vpc)


def test_validate_vpc_not_exists(vpc_configurator):
    """Test validating a VPC that doesn't exist."""
    # VPC should not exist
    assert not vpc_configurator._validate_vpc('vpc-12345')


def test_validate_subnets_valid(vpc_configurator, test_vpc, test_subnets):
    """Test validating subnets that exist and belong to the VPC."""
    # Subnets should be valid
    assert vpc_configurator._validate_subnets(test_subnets, test_vpc)


def test_validate_subnets_invalid_vpc(vpc_configurator, test_subnets):
    """Test validating subnets with an invalid VPC."""
    # Subnets should not be valid with an invalid VPC
    assert not vpc_configurator._validate_subnets(test_subnets, 'vpc-12345')


def test_validate_subnets_not_exist(vpc_configurator, test_vpc):
    """Test validating subnets that don't exist."""
    # Subnets should not be valid
    assert not vpc_configurator._validate_subnets(['subnet-12345'], test_vpc)


def test_validate_security_groups_valid(vpc_configurator, test_vpc, test_security_group):
    """Test validating security groups that exist and belong to the VPC."""
    # Security group should be valid
    assert vpc_configurator._validate_security_groups([test_security_group], test_vpc)


def test_validate_security_groups_invalid_vpc(vpc_configurator, test_security_group):
    """Test validating security groups with an invalid VPC."""
    # Security group should not be valid with an invalid VPC
    assert not vpc_configurator._validate_security_groups([test_security_group], 'vpc-12345')


def test_validate_security_groups_not_exist(vpc_configurator, test_vpc):
    """Test validating security groups that don't exist."""
    # Security group should not be valid
    assert not vpc_configurator._validate_security_groups(['sg-12345'], test_vpc)


def test_create_vpc_config(vpc_configurator, test_vpc, test_subnets, test_security_group):
    """Test creating a VPC configuration."""
    # Create VPC configuration
    vpc_config = vpc_configurator.create_vpc_config(
        vpc_id=test_vpc,
        subnet_ids=test_subnets,
        security_group_ids=[test_security_group]
    )
    
    # Verify the VPC configuration
    assert vpc_config['SubnetIds'] == test_subnets
    assert vpc_config['SecurityGroupIds'] == [test_security_group]


def test_create_vpc_config_no_security_groups(vpc_configurator, test_vpc, test_subnets):
    """Test creating a VPC configuration without security groups."""
    # Create VPC configuration
    vpc_config = vpc_configurator.create_vpc_config(
        vpc_id=test_vpc,
        subnet_ids=test_subnets
    )
    
    # Verify the VPC configuration
    assert vpc_config['SubnetIds'] == test_subnets
    assert 'SecurityGroupIds' not in vpc_config


def test_create_vpc_config_invalid_vpc(vpc_configurator, test_subnets):
    """Test creating a VPC configuration with an invalid VPC."""
    # Should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        vpc_configurator.create_vpc_config(
            vpc_id='vpc-12345',
            subnet_ids=test_subnets
        )
    
    # Verify the error message
    assert "Invalid VPC" in str(excinfo.value)


def test_create_vpc_config_invalid_subnets(vpc_configurator, test_vpc):
    """Test creating a VPC configuration with invalid subnets."""
    # Should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        vpc_configurator.create_vpc_config(
            vpc_id=test_vpc,
            subnet_ids=['subnet-12345']
        )
    
    # Verify the error message
    assert "Invalid subnets" in str(excinfo.value)


def test_create_vpc_config_invalid_security_groups(vpc_configurator, test_vpc, test_subnets):
    """Test creating a VPC configuration with invalid security groups."""
    # Should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        vpc_configurator.create_vpc_config(
            vpc_id=test_vpc,
            subnet_ids=test_subnets,
            security_group_ids=['sg-12345']
        )
    
    # Verify the error message
    assert "Invalid security groups" in str(excinfo.value)


def test_get_available_vpcs(vpc_configurator, test_vpc, ec2_client):
    """Test getting available VPCs."""
    # Get available VPCs
    vpcs = vpc_configurator.get_available_vpcs()
    
    # Verify the VPCs - moto creates a default VPC, so we need to check for our test VPC specifically
    assert len(vpcs) >= 1
    
    # Find our test VPC in the list
    test_vpc_found = False
    for vpc in vpcs:
        if vpc['id'] == test_vpc:
            assert vpc['cidr'] == '10.0.0.0/16'
            assert vpc['name'] == 'test-vpc'
            test_vpc_found = True
            break
    
    assert test_vpc_found, f"Test VPC {test_vpc} not found in available VPCs"


def test_get_subnets_for_vpc(vpc_configurator, test_vpc, test_subnets):
    """Test getting subnets for a VPC."""
    # Get subnets for the VPC
    subnets = vpc_configurator.get_subnets_for_vpc(test_vpc)
    
    # Verify the subnets
    assert len(subnets) == 2
    assert subnets[0]['id'] in test_subnets
    assert subnets[1]['id'] in test_subnets
    assert subnets[0]['cidr'] in ['10.0.1.0/24', '10.0.2.0/24']
    assert subnets[1]['cidr'] in ['10.0.1.0/24', '10.0.2.0/24']
    assert subnets[0]['az'] in ['us-east-1a', 'us-east-1b']
    assert subnets[1]['az'] in ['us-east-1a', 'us-east-1b']
    assert subnets[0]['name'] in ['test-subnet-1', 'test-subnet-2']
    assert subnets[1]['name'] in ['test-subnet-1', 'test-subnet-2']


def test_get_security_groups_for_vpc(vpc_configurator, test_vpc, test_security_group):
    """Test getting security groups for a VPC."""
    # Get security groups for the VPC
    security_groups = vpc_configurator.get_security_groups_for_vpc(test_vpc)
    
    # Verify the security groups - moto creates a default security group, so we need to check for our test security group specifically
    assert len(security_groups) >= 1
    
    # Find our test security group in the list
    test_sg_found = False
    for sg in security_groups:
        if sg['id'] == test_security_group:
            assert sg['name'] == 'test-sg'
            assert sg['description'] == 'Test security group'
            test_sg_found = True
            break
    
    assert test_sg_found, f"Test security group {test_security_group} not found in security groups for VPC {test_vpc}"
