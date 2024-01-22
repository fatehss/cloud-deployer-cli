import boto3
import ipaddress



class VPCSetup:
    def __init__(self, vpc_name = 'cloud-deployer-vpc',region="us-east-1", cidr_block='10.0.0.0/16', num_public_subnets = 2, num_private_subnets=2):
        self.name = vpc_name
        self.region = region
        self.cidr_block= cidr_block
        self.ec2_resource = boto3.resource('ec2', region_name=region)
        self.num_public_subnets = num_public_subnets
        self.num_private_subnets = num_private_subnets

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
        vpc.create_tags(Tags=[{"Key": "Name", "Value": self.name}])
        vpc.wait_until_available()
        return vpc

    def setup_internet_gateway(self, vpc):
        igw = self.ec2_resource.create_internet_gateway()
        vpc.attach_internet_gateway(InternetGatewayId=igw.id)
        return igw

    def create_route_table(self, vpc, igw):
        route_table = vpc.create_route_table()
        route_table.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=igw.id)
        return route_table

    def create_subnets(self, vpc):
        #this function creates both public and private subnets
        public_subnets, private_subnets = [], []
        SUBNET_PREFIX = 24
        start_network = ipaddress.ip_network(self.cidr_block)
        
        for i in range(self.num_public_subnets + self.num_private_subnets):
            next_cidr = str(ipaddress.ip_network((int(start_network.network_address) + (i + 1) * (2 ** (32 - SUBNET_PREFIX)), SUBNET_PREFIX)))
            subnet = self.ec2_resource.create_subnet(CidrBlock=next_cidr, VpcId=vpc.id)
            if i < self.num_public_subnets:
                public_subnets.append(subnet.id)
            else:
                private_subnets.append(subnet.id)

        return public_subnets, private_subnets

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
        

def list_s3():
    s3 = boto3.resource('s3')
    for bucket in s3.buckets.all():
        print(bucket.name)
if __name__ == "__main__":
    test_deployment = VPCSetup()
    test_deployment.setup()


