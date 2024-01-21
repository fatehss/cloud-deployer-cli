import boto3
import pprint
import ipaddress

def find_start_cidr(start_cidr, cidr_ranges):
    """
    Increments the starting CIDR block if it overlaps with any in the provided list.
    Finds the new starting CIDR if overlaps occur
    :param start_cidr: The starting CIDR block in the format '10.0.0.0/y'.
    :param cidr_ranges: A list of CIDR ranges to check for overlap.
    :return: A non-overlapping CIDR block.
    """
    start_network = ipaddress.ip_network(start_cidr)
    y = start_network.prefixlen

    while any(start_network.overlaps(ipaddress.ip_network(cidr)) for cidr in cidr_ranges):
        # Move to the next network block by adding the number of addresses in the network
        start_network = ipaddress.ip_network((int(start_network.network_address) + start_network.num_addresses, y))

    return str(start_network)


def list_s3():
    s3 = boto3.resource('s3')
    for bucket in s3.buckets.all():
        print(bucket.name)


def VPC_setup(start_cidr='10.0.0.0/16', region="us-east-1", name = "cloud-deployer-vpc", num_public_subnets = 2, num_private_subnets = 2):

    client = boto3.client('ec2',region_name=region) #check vpcs
    response = client.describe_vpcs()
    if response:
        vpcs = response["Vpcs"]
        cidrs= [vpc["CidrBlock"] for vpc in vpcs]
        start_cidr = find_start_cidr(start_cidr, cidrs)

        #vpc creation process
        ec2 = boto3.resource('ec2', region_name = region)
        vpc = ec2.create_vpc(CidrBlock=start_cidr)
        vpc.create_tags(Tags=[{"Key": "Name", "Value": name}])
        vpc.wait_until_available()
        print(f"vpc id:{vpc.id}")

        #igw setup process
        ig = ec2.create_internet_gateway()
        vpc.attach_internet_gateway(InternetGatewayId=ig.id)
        print(f"igw id: {ig.id}")

        #route table setup
        route_table = vpc.create_route_table()
        route = route_table.create_route(
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=ig.id
        )
        print(f"route table id: {route_table.id}")


        #create subnets
        public_subnets, private_subnets = [], []
        for i in range(num_public_subnets+num_private_subnets):
            #create both public and private sn's in one loop
            #get the correct cidr range for the sn
            SUBNET_PREFIX = 24

            start_network = ipaddress.ip_network(start_cidr)
            next_cidr = str(ipaddress.ip_network((int(start_network.network_address)+(i+1)*(2**(32-SUBNET_PREFIX)), SUBNET_PREFIX)))
            
            subnet = ec2.create_subnet(CidrBlock=next_cidr, VpcId=vpc.id)
            
            if i<num_public_subnets: #if this is a public subnet
                route_table.associate_with_subnet(SubnetId=subnet.id) #associate with route table for public subnets
                public_subnets.append(subnet.id)
            else:   #if private
                private_subnets.append(subnet.id)

        print(f"public subnets: {public_subnets}")
        print(f"private subnets: {private_subnets}")
        # EC2_SG = ec2.create_security_group(
        #     GroupName="EC2_SG", Description="EC2 security group allowing inbound ssh traffic", VpcId=vpc.id)
        # RDS_EC2_SG = ec2.create_security_group(
        #     GroupName="RDS-EC2-sg", Description="Security group allowing inbound traffic from ec2 instances", VpcId=vpc.id)
            

    else:
        print("no response")

if __name__ == "__main__":
    #list_s3()
    VPC_setup()

#the perfect tutorial: https://gist.github.com/nguyendv/8cfd92fc8ed32ebb78e366f44c2daea6

#attach igw via 
#   ig = ec2.create_internet_gateway()
#   vpc.attach_internet_gateway(InternetGatewayId=ig.id)
    
#note: need to add eni and allow routing from public internet via ssh for ec2
#what happens: 
'''
What exactly is going on:

1. VPC is created in the correct cidr range
2. An internet gateway is created for the VPC

'''