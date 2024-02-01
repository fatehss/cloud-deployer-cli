# cloud-deployer
Python CLI application that deploys a 2/3 tier architecture to cloud services. Made with Boto3 instead of Terraform mainly for learning purposes. Will deploy multiple EC2 instances in a user-specified number of public subnets across AZs with a MySQL RDS instance in private subnets, and an optional application load balancer. The EC2 instances are bootstrapped with userdata to automatically have MySQL configured. The CLI will handle all the networking configurations within a VPC for this free-tier setup. Finally, the SSH key pair for connecting to the EC2 instances is generated and stored locally.
You need python3 installed for this to work.

Setup steps:

1. Run "pip install ." in the directory containing setup.py
2. Follow [these instructions](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) to setup aws cli 

The CLI has two command:

1. ```cloud-deployer setup``` - sets up the VPC config
2. ```cloud-deployer cleanup``` - terminates ec2 instances, deletes RDS DB, and removes all infrastructure for the VPC


## Sample Output

For this example, we create the entire 3-tier architecture:
### *Running setup*
![Screenshot from 2024-02-01 12-00-53](https://github.com/fatehss/cloud-deployer-cli/assets/104878259/9baccfdd-f3fc-4b31-96e0-cb04fa3466d2)

This creates all the infrastructure we need. Here are what the VPC and instances look like in the aws console:

![Screenshot from 2024-02-01 12-08-47](https://github.com/fatehss/cloud-deployer-cli/assets/104878259/421c6391-5f1f-4b9d-b792-d319735ea48b)
![Screenshot from 2024-02-01 12-08-59](https://github.com/fatehss/cloud-deployer-cli/assets/104878259/86928fe7-7992-4059-86ba-612d372af292)
![Screenshot from 2024-02-01 12-17-52](https://github.com/fatehss/cloud-deployer-cli/assets/104878259/106228de-12b3-47af-b627-f5e5f6e35879)


### *Running cleanup*
![Screenshot from 2024-02-01 12-15-36](https://github.com/fatehss/cloud-deployer-cli/assets/104878259/de7b06a3-5ecf-4ed9-915c-534d1aad402b)

Everything in the VPC, including all instances, route tables, security groups, etc. are terminated.
