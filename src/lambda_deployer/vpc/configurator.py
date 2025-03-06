"""
VPC configurator for Lambda functions.
Handles VPC configuration for Lambda functions.
"""
import logging
from typing import Dict, List, Optional, Union

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class VPCConfigurator:
    """
    Configures VPC settings for Lambda functions.
    
    This class handles:
    - Validating VPC, subnet, and security group configurations
    - Creating VPC configuration for Lambda functions
    - Checking VPC resource permissions
    """
    
    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize the VPC configurator.
        
        Args:
            region_name: AWS region name. If not provided, uses the default region.
        """
        self.ec2_client = boto3.client('ec2', region_name=region_name)
    
    def _validate_vpc(self, vpc_id: str) -> bool:
        """
        Validate that a VPC exists and is available.
        
        Args:
            vpc_id: ID of the VPC to validate
            
        Returns:
            True if the VPC exists and is available, False otherwise
        """
        try:
            response = self.ec2_client.describe_vpcs(VpcIds=[vpc_id])
            
            if not response.get('Vpcs'):
                logger.warning(f"VPC {vpc_id} does not exist")
                return False
            
            vpc_state = response['Vpcs'][0].get('State')
            if vpc_state != 'available':
                logger.warning(f"VPC {vpc_id} is not available (state: {vpc_state})")
                return False
            
            logger.info(f"VPC {vpc_id} exists and is available")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidVpcID.NotFound':
                logger.warning(f"VPC {vpc_id} does not exist")
                return False
            else:
                logger.error(f"Error validating VPC {vpc_id}: {e}")
                raise
    
    def _validate_subnets(self, subnet_ids: List[str], vpc_id: str) -> bool:
        """
        Validate that subnets exist, are available, and belong to the specified VPC.
        
        Args:
            subnet_ids: List of subnet IDs to validate
            vpc_id: ID of the VPC that the subnets should belong to
            
        Returns:
            True if all subnets are valid, False otherwise
        """
        try:
            response = self.ec2_client.describe_subnets(SubnetIds=subnet_ids)
            
            if len(response.get('Subnets', [])) != len(subnet_ids):
                logger.warning(f"Not all subnets in {subnet_ids} exist")
                return False
            
            for subnet in response['Subnets']:
                if subnet.get('VpcId') != vpc_id:
                    logger.warning(f"Subnet {subnet.get('SubnetId')} does not belong to VPC {vpc_id}")
                    return False
                
                if subnet.get('State') != 'available':
                    logger.warning(f"Subnet {subnet.get('SubnetId')} is not available (state: {subnet.get('State')})")
                    return False
            
            logger.info(f"All subnets {subnet_ids} exist, are available, and belong to VPC {vpc_id}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidSubnetID.NotFound':
                logger.warning(f"One or more subnets in {subnet_ids} do not exist")
                return False
            else:
                logger.error(f"Error validating subnets {subnet_ids}: {e}")
                raise
    
    def _validate_security_groups(self, security_group_ids: List[str], vpc_id: str) -> bool:
        """
        Validate that security groups exist and belong to the specified VPC.
        
        Args:
            security_group_ids: List of security group IDs to validate
            vpc_id: ID of the VPC that the security groups should belong to
            
        Returns:
            True if all security groups are valid, False otherwise
        """
        try:
            response = self.ec2_client.describe_security_groups(GroupIds=security_group_ids)
            
            if len(response.get('SecurityGroups', [])) != len(security_group_ids):
                logger.warning(f"Not all security groups in {security_group_ids} exist")
                return False
            
            for sg in response['SecurityGroups']:
                if sg.get('VpcId') != vpc_id:
                    logger.warning(f"Security group {sg.get('GroupId')} does not belong to VPC {vpc_id}")
                    return False
            
            logger.info(f"All security groups {security_group_ids} exist and belong to VPC {vpc_id}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidGroup.NotFound':
                logger.warning(f"One or more security groups in {security_group_ids} do not exist")
                return False
            else:
                logger.error(f"Error validating security groups {security_group_ids}: {e}")
                raise
    
    def create_vpc_config(
        self,
        vpc_id: str,
        subnet_ids: List[str],
        security_group_ids: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        """
        Create a VPC configuration for a Lambda function.
        
        Args:
            vpc_id: ID of the VPC
            subnet_ids: List of subnet IDs
            security_group_ids: List of security group IDs (optional)
            
        Returns:
            VPC configuration dictionary for Lambda function
            
        Raises:
            ValueError: If VPC, subnets, or security groups are invalid
        """
        # Validate VPC
        if not self._validate_vpc(vpc_id):
            raise ValueError(f"Invalid VPC: {vpc_id}")
        
        # Validate subnets
        if not self._validate_subnets(subnet_ids, vpc_id):
            raise ValueError(f"Invalid subnets: {subnet_ids}")
        
        # Validate security groups if provided
        if security_group_ids and not self._validate_security_groups(security_group_ids, vpc_id):
            raise ValueError(f"Invalid security groups: {security_group_ids}")
        
        # Create VPC configuration
        vpc_config = {
            'SubnetIds': subnet_ids
        }
        
        if security_group_ids:
            vpc_config['SecurityGroupIds'] = security_group_ids
        
        logger.info(f"Created VPC configuration: {vpc_config}")
        return vpc_config
    
    def get_available_vpcs(self) -> List[Dict[str, str]]:
        """
        Get a list of available VPCs.
        
        Returns:
            List of dictionaries containing VPC information (id, cidr, name)
        """
        try:
            response = self.ec2_client.describe_vpcs()
            
            vpcs = []
            for vpc in response.get('Vpcs', []):
                if vpc.get('State') == 'available':
                    vpc_info = {
                        'id': vpc.get('VpcId'),
                        'cidr': vpc.get('CidrBlock')
                    }
                    
                    # Get VPC name if available
                    for tag in vpc.get('Tags', []):
                        if tag.get('Key') == 'Name':
                            vpc_info['name'] = tag.get('Value')
                            break
                    
                    vpcs.append(vpc_info)
            
            return vpcs
            
        except ClientError as e:
            logger.error(f"Error getting available VPCs: {e}")
            raise
    
    def get_subnets_for_vpc(self, vpc_id: str) -> List[Dict[str, str]]:
        """
        Get a list of subnets for a VPC.
        
        Args:
            vpc_id: ID of the VPC
            
        Returns:
            List of dictionaries containing subnet information (id, az, cidr, name)
        """
        try:
            response = self.ec2_client.describe_subnets(
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_id]
                    }
                ]
            )
            
            subnets = []
            for subnet in response.get('Subnets', []):
                if subnet.get('State') == 'available':
                    subnet_info = {
                        'id': subnet.get('SubnetId'),
                        'az': subnet.get('AvailabilityZone'),
                        'cidr': subnet.get('CidrBlock')
                    }
                    
                    # Get subnet name if available
                    for tag in subnet.get('Tags', []):
                        if tag.get('Key') == 'Name':
                            subnet_info['name'] = tag.get('Value')
                            break
                    
                    subnets.append(subnet_info)
            
            return subnets
            
        except ClientError as e:
            logger.error(f"Error getting subnets for VPC {vpc_id}: {e}")
            raise
    
    def get_security_groups_for_vpc(self, vpc_id: str) -> List[Dict[str, str]]:
        """
        Get a list of security groups for a VPC.
        
        Args:
            vpc_id: ID of the VPC
            
        Returns:
            List of dictionaries containing security group information (id, name, description)
        """
        try:
            response = self.ec2_client.describe_security_groups(
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_id]
                    }
                ]
            )
            
            security_groups = []
            for sg in response.get('SecurityGroups', []):
                security_groups.append({
                    'id': sg.get('GroupId'),
                    'name': sg.get('GroupName'),
                    'description': sg.get('Description')
                })
            
            return security_groups
            
        except ClientError as e:
            logger.error(f"Error getting security groups for VPC {vpc_id}: {e}")
            raise
