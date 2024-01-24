import os
import os.path
import typer
import ipaddress

from cloud_deployer.aws_functions import USERDATA_SCRIPT, VPCSetup


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