import boto3
import ipaddress

import random

USERDATA_SCRIPT = '''#!/bin/bash
sudo dnf update -y
sudo dnf install -y mariadb105
'''
class VPCSetup:
    def __init__(self, vpc_name = 'cloud-deployer-vpc',region="us-east-1", cidr_block='10.0.0.0/16', num_public_subnets = 2, num_private_subnets=2, include_load_balancer=False):
        self.name = vpc_name
        self.region = region
        self.cidr_block= cidr_block
        self.ec2_resource = boto3.resource('ec2', region_name=region)
        self.num_public_subnets = num_public_subnets
        self.num_private_subnets = num_private_subnets
        self.load_balancer = include_load_balancer
        self.userdata = USERDATA_SCRIPT
        self.suffix = ''
        if vpc_name == 'cloud-deployer-vpc':
            self.suffix =  '-'+str(random.randint(1,100000)) #this is for distinguishing the vpcs connected

    def cidr_correction(self):
        '''
        Function to find the next closest cidr block to the one provided
        '''
        client = boto3.client('ec2',region_name=self.region) #check vpcs
        response = client.describe_vpcs()
        if not response:
            print("failed to connect to aws cli")
            exit(1)
        exisiting_vpcs = response["Vpcs"]
        existing_cidrs = [vpc["CidrBlock"] for vpc in exisiting_vpcs]

        start_network = ipaddress.ip_network(self.cidr_block) #find the starting cidr block to check from
        cidr_mask = start_network.prefixlen
        while any(start_network.overlaps(ipaddress.ip_network(cidr)) for cidr in existing_cidrs):
            # Move to the next network block by adding the number of addresses in the network
            start_network = ipaddress.ip_network((int(start_network.network_address) + start_network.num_addresses, cidr_mask))

        return str(start_network)

    def create_vpc(self):

        vpc = self.ec2_resource.create_vpc(CidrBlock=self.cidr_block)
        vpc.create_tags(Tags=[{"Key": "Name", "Value": self.name+self.suffix}])
        vpc.wait_until_available()
        return vpc

    def setup_internet_gateway(self, vpc):
        igw = self.ec2_resource.create_internet_gateway()
        vpc.attach_internet_gateway(InternetGatewayId=igw.id)
        return igw

    def create_route_table(self, vpc, igw):
        route_table = vpc.create_route_table()
        route_table.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=igw.id)
        route_table.create_tags(Tags=[{'Key': 'Name', 'Value': f"{self.name+self.suffix} public vpc rt"}])
        return route_table

    def create_subnets(self, vpc):
        #this function creates both public and private subnets

        #idea is to ensure creattion of subnets in different azs in the region
        def get_number_of_azs(region_name):
            ec2_client = boto3.client('ec2', region_name=region_name)
            response = ec2_client.describe_availability_zones()
            azs = response['AvailabilityZones']
            return len([az for az in azs if az['State'] == 'available'])

        num_azs_available = get_number_of_azs(self.region)  
        azs = ['a','b','c','d','e','f'] #max of 6 azs per region (as of jan 2024)

        public_subnets, private_subnets = [], []
        SUBNET_PREFIX = 24
        curr_cidr = ipaddress.ip_network(self.cidr_block)
    
        for i in range(self.num_public_subnets):
            next_cidr = str(ipaddress.ip_network((int(curr_cidr.network_address) + (i + 1) * (2 ** (32 - SUBNET_PREFIX)), SUBNET_PREFIX))) #increment current cidr
            subnet = self.ec2_resource.create_subnet(CidrBlock=next_cidr, VpcId=vpc.id, AvailabilityZone=self.region+azs[i%num_azs_available])
            subnet.create_tags(Tags=[{'Key': 'Name', 'Value': f"{self.name+self.suffix} Public-Subnet-{i+1}"}])
            public_subnets.append(subnet.id)
      
        for i in range(self.num_private_subnets):
            next_cidr= str(ipaddress.ip_network((int(curr_cidr.network_address) + (i + 1+self.num_public_subnets) * (2 ** (32 - SUBNET_PREFIX)), SUBNET_PREFIX))) #increment current cidr
            subnet = self.ec2_resource.create_subnet(CidrBlock=next_cidr, VpcId=vpc.id, AvailabilityZone=self.region+azs[i%num_azs_available])
            subnet.create_tags(Tags=[{'Key': 'Name', 'Value': f"{self.name+self.suffix} Private-Subnet-{i+1}"}])
            private_subnets.append(subnet.id)

        return public_subnets, private_subnets
    
    def create_ec2_instances(self, public_subnets, ec2_sg):
        # TODO: Add script that searches for AMIs instead of hardcoding them
        instance_list = []
        #linux 2 ami for 2024 in us-east-1 - ami-0c0b74d29acd0cd97 
        #amazon linux ami: ami-0a3c3a20c09d6f377
        ami = 'ami-0a3c3a20c09d6f377'
        for i, sn in enumerate(public_subnets):
            instance = self.ec2_resource.create_instances(
                ImageId=ami,
                InstanceType='t2.micro',
                MaxCount=1,
                MinCount=1,
                UserData=self.userdata,
                NetworkInterfaces=[{
                    'SubnetId': sn,
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'Groups': [ec2_sg.group_id]
                }],
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': f'{self.name+self.suffix}-{1+i}'}
                        ]
                    }
                ]
            )
            instance[0].wait_until_exists()
            instance_list.append(instance[0])

        return instance_list

    def create_ec2_rds_security_groups(self,vpc):


         #Create EC2 Security Group
        ec2_sg = self.ec2_resource.create_security_group(
            GroupName=f"EC2_SG vpc-{self.name+self.suffix}",
            Description="EC2 security group allowing inbound SSH traffic and outbound traffic to RDS",
            VpcId=vpc.id
        )
        ec2_sg.create_tags(Tags=[{'Key': 'Name', 'Value': f"EC2-SG-{self.name+self.suffix}"}])

        # Create RDS Security Group
        rds_sg = self.ec2_resource.create_security_group(
            GroupName=f"RDS-SG vpc-{self.name+self.suffix}",
            Description="Security group allowing inbound MySQL traffic from EC2 instances",
            VpcId=vpc.id
        )
        rds_sg.create_tags(Tags=[{'Key': 'Name', 'Value': f"RDS-SG-{self.name+self.suffix}"}])

        # Add inbound rule to EC2 Security Group for SSH
        ec2_sg.authorize_ingress(
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        # Add inbound rule to RDS Security Group for MySQL from EC2 Security Group
        rds_sg.authorize_ingress(
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 3306,
                    'ToPort': 3306,
                    'UserIdGroupPairs': [{'GroupId': ec2_sg.group_id}]
                }
            ]
        )

        return ec2_sg, rds_sg

    def rds_setup(self, private_subnets, rds_sg):
        sn_group_name = f'{self.name+self.suffix} rds subnet group-'
        rds_client = boto3.client('rds', region_name=self.region)
        rds_client.create_db_subnet_group(
            DBSubnetGroupName=sn_group_name,
            DBSubnetGroupDescription='Subnet group for rds instance via cloud-deployer',
            SubnetIds = private_subnets,
            )


        DB_NAME = f'cloud-deployer-n{self.suffix}-db'
        DB_USERNAME = "admin"
        DB_PASSWORD = "MYPASSWORD"
        try:
            db_instance = rds_client.create_db_instance(
                DBInstanceIdentifier=DB_NAME,
                AllocatedStorage=20,  # Minimum storage in GB for free tier
                DBInstanceClass='db.t2.micro',  # Free tier eligible instance class
                Engine='mysql',
                MasterUsername=DB_USERNAME,
                MasterUserPassword=DB_PASSWORD,
                VpcSecurityGroupIds=[rds_sg.id],
                DBSubnetGroupName=sn_group_name,
                MultiAZ=False,
                StorageType='gp2',
                BackupRetentionPeriod=7,  # Default retention period
                Port=3306,
                PubliclyAccessible=False,
            Tags=[
                {'Key': 'Name', 'Value': DB_NAME}]
            )
            return db_instance
        except Exception as e:
            print(f"Error creating RDS instance: {e}")
            return None
        
#     def create_load_balancer(self, subnets):
#         autoscaling = boto3.client('autoscaling')

#         # Create launch configuration
#         autoscaling.create_launch_configuration(
#             LaunchConfigurationName='my-launch-configuration',
#             ImageId='ami-xxxxxx',  # replace with your chosen AMI ID
#             InstanceType='t2.micro',  # replace with your chosen instance type
#             SecurityGroups=[
#                 'sg-xxxxxx',  # replace with your security group ID
#             ],
#             IamInstanceProfile='my-iam-role'  # replace with your IAM role if necessary
#         )

#         # Create auto scaling group
#         autoscaling.create_auto_scaling_group(
#             AutoScalingGroupName='my-auto-scaling-group',
#             LaunchConfigurationName='my-launch-configuration',
#             MinSize=1,
#             MaxSize=3,
#             DesiredCapacity=2,
#             VPCZoneIdentifier='subnet-xxxxxx,subnet-yyyyyy',  # replace with your subnet IDs
#             TargetGroupARNs=[target_group_arn],
#             HealthCheckType='ELB',
#             HealthCheckGracePeriod=300
#         )
# `

        
    def setup(self):
        # Implement the logic to set up VPC, subnets, and security groups
        # ...

        self.cidr_block = self.cidr_correction()
        vpc = self.create_vpc()
        print(f"vpc id: {vpc.id}")
        igw = self.setup_internet_gateway(vpc)
        print(f"igw id: {igw.id}")
        rt = self.create_route_table(vpc, igw)
        print(f"rt id: {rt.id}")
        public_subnets, private_subnets = self.create_subnets(vpc)
        for sn in public_subnets:
            rt.associate_with_subnet(SubnetId=sn)
        print(f"public subnets: {public_subnets}\nprivate subnet: {private_subnets}")
        ec2_sg, rds_sg = self.create_ec2_rds_security_groups(vpc)  
        print(f"Security groups: {[rds_sg.id, ec2_sg.id]}")

        #create ec2 instances
        instances = self.create_ec2_instances(public_subnets, ec2_sg)
        for i in instances:
            print(f"ec2 instance id: {i.id}")
        # create rds instance
        rds_instance = self.rds_setup(private_subnets, rds_sg)
        print(f"RDS db instance created")
'''
TODO:

configure security groups for rds (rds_sg currently is not associated to instance)
set up automatic connction to ec2 instances from rds 

add the following userdata to the ec2 instances: 

sudo yum install mysql -y  # For Amazon Linux, CentOS, RHEL
sudo apt-get install mysql-client -y  # For Ubuntu, Debian

'''
'''
EC2 User Data + db connection

sudo dnf update -y
sudo dnf install mariadb105


db connection:
mysql -h [endpoint] -P 3306 -u [username] -p


'''


        

def list_s3():
    s3 = boto3.resource('s3')
    for bucket in s3.buckets.all():
        print(bucket.name)

if __name__ == "__main__":
    test_deployment = VPCSetup()
    test_deployment.setup()


