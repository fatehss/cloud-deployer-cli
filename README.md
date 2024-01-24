# cloud-deployer
Proof-of-concept Python CLI application that deploys a 2/3 tier architecture to cloud services. Made with Boto3 instead of Terraform mainly for learning purposes. Will deploy multiple EC2 instances in a user-specified number of public subnets across AZs with a MySQL RDS instance in private subnets, and an optional application load balancer. The CLI will handle all the networking configurations within a VPC for this free-tier setup.
You need python3 installed for this to work.

Setup steps:

1. Run "pip install ." in the directory containing this file
2. Follow [these instructions](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) to setup aws cli 

The CLI has two command:

1. ```cloud-deployer setup``` - sets up the VPC config
2. ```cloud-deployer cleanup``` - terminates ec2 instances, deletes RDS DB, and removes all infrastructure for the VPC
