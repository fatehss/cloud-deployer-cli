import os.path
import typer
import ipaddress
import boto3

from cloud_deployer.aws_functions import USERDATA_SCRIPT, VPCSetup
from cloud_deployer.vpc_cleanup import delete_infrastructure


app = typer.Typer()


def validate_cidr_block(value: str):
    try:
        ipaddress.ip_network(value)
    except ValueError:
        raise typer.BadParameter("Invalid CIDR block format")
    return value
def subnet_limits(num: int):
    return num <1 or num >9

@app.command()
def setup():
    vpc_name = typer.prompt("VPC name", default="cloud-deployer-vpc")
    region = typer.prompt("Region", default="us-east-1")
    cidr_block = typer.prompt("CIDR block", default="10.0.0.0/16", value_proc=validate_cidr_block)
    num_public_subnets = typer.prompt("Number of public subnets", type=int, default=2)
    ec2_ami = typer.prompt("AMI to use for ec2 (default is amazon linux)", default = "ami-0277155c3f0ab2930")
    include_load_balancer = typer.confirm("Include load balancer?", default=False)
    create_rds = typer.confirm("Create Database?", default=False)
    

    num_private_subnets = typer.prompt("Number of private subnets for RDS", type=int, default=2)
    db_admin_username = "admin"
    db_password = "mypassword"
    
    if create_rds:
        db_admin_username = typer.prompt("Database Admin Username", default="admin")
        db_password = typer.prompt("Database Admin Password", hide_input=True)
 
    try:
        print('\n')
        vpc = VPCSetup(vpc_name=vpc_name, region=region, cidr_block=cidr_block, num_public_subnets=num_public_subnets,ec2_ami=ec2_ami, num_private_subnets=num_private_subnets, create_rds=create_rds, db_admin_username=db_admin_username, db_password=db_password, include_load_balancer=include_load_balancer)
        vpc.setup()
    except Exception as e:
        print(e)
        

@app.command()
def cleanup():
    def get_vpc_name(tags):
        """Extract the name from VPC tags."""
        if tags is None:
            return "No Name"
        for tag in tags:
            if tag['Key'] == 'Name':
                return tag['Value']
        return "No Name"

    ec2_client = boto3.client('ec2')

    # Describe all VPCs
    response = ec2_client.describe_vpcs()
    vpcs = response['Vpcs']

    # Filter out the default VPCs and get their names
    non_default_vpcs = []
    print("Current VPCs in account:\n")
    for vpc in vpcs:
        if not vpc['IsDefault']:
            vpc_name = get_vpc_name(vpc.get('Tags', []))
            print(f"VPC ID: {vpc['VpcId']} - Name: {vpc_name} - State: {vpc['State']} - CIDR: {vpc['CidrBlock']}")
    print('\n')

    available_vpcs =  [vpc['VpcId'] for vpc in vpcs]
    vpc_id = typer.prompt("Enter VPC ID of VPC to be removed")
    if vpc_id not in available_vpcs:
        print("Invalid VPC ID")
    else:
        delete_infrastructure(vpc_id)

@app.command()
def bye():
    typer.echo("bye")

if __name__ == "__main__":
    app()


'''
vpc name (default: cloud-deployer): [input]
region (default: us-east-1): [input]
cidr block (default: 10.0.0.0/16):
number of public subnets (default: 2): [input]
number of private subnets for rds (default: 2): [input]
''' 
