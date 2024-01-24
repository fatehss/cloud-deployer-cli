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
    vpc_name = typer.prompt("VPC name", default="cloud-deployer")
    region = typer.prompt("Region", default="us-east-1")
    cidr_block = typer.prompt("CIDR block", default="10.0.0.0/16", value_proc=validate_cidr_block)
    num_public_subnets = typer.prompt("Number of public subnets", type=int, default=2)
    num_private_subnets = typer.prompt("Number of private subnets for RDS", default=2)


    try:
        print("called function")
        vpc = VPCSetup(vpc_name, region, cidr_block, num_public_subnets, num_private_subnets)
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
    vpc_id = typer.prompt("Enter VPC ID of VPC to be removed:")
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