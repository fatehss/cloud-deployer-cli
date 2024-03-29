
import boto3
import threading
import time
VERBOSE = 1


def del_igw(ec2, vpcid):
    """Detach and delete the internet-gateway"""
    vpc_resource = ec2.Vpc(vpcid)
    igws = vpc_resource.internet_gateways.all()

    if igws:
        for igw in igws:
            while True:
                try:
                    igw.detach_from_vpc(VpcId=vpcid)
                    igw.delete()
                    print("Detaching and Removing igw-id: ", igw.id) if (VERBOSE == 1) else ""
                    break  # Break the loop if successful
                except Exception as e:
                    time.sleep(5)  # Wait for 5 seconds before retrying

def del_sub(ec2, vpcid):
    """Delete the subnets"""
    vpc_resource = ec2.Vpc(vpcid)
    subnets = vpc_resource.subnets.all()
    default_subnets = [ec2.Subnet(subnet.id) for subnet in subnets]

    if default_subnets:
        for sub in default_subnets: 
            while True:
                try:
                    print("Removing sub-id: ", sub.id) if VERBOSE else ""
                    sub.delete()
                    break  # Break the loop if successful
                except Exception as e:
                    #print(f"An error occurred: {e}")
                    time.sleep(3)  # Wait for 5 seconds before retrying

def del_rtb(ec2, vpcid):
  """ Delete the route-tables """
  vpc = ec2.Vpc(vpcid)
  ec2_client = boto3.client('ec2')
# Delete routes and route tables
  for rt in vpc.route_tables.all():
    for route in rt.routes_attribute:
        if route.get('Origin') == 'CreateRoute':
            ec2_client.delete_route(RouteTableId=rt.id, DestinationCidrBlock=route['DestinationCidrBlock'])
    try:
        rt.delete()
    except Exception as e:
        x=1 #skip
        #print(f"Could not delete route table {rt.id}: {e}")
  print("Routes and route tables deleted.")

def del_acl(ec2, vpcid):
  """ Delete the network-access-lists """
  
  vpc_resource = ec2.Vpc(vpcid)      
  acls = vpc_resource.network_acls.all()

  if acls:
    try:
      for acl in acls: 
        if acl.is_default:
          print(acl.id + " is the default NACL, continue...")
          continue
        print("Removing acl-id: ", acl.id) if (VERBOSE == 1) else ""
        acl.delete(
          # DryRun=True
        )
    except boto3.exceptions.Boto3Error as e:
      print(e)

def del_sgp(ec2, vpcid):
    """Delete any security-groups"""
    vpc_resource = ec2.Vpc(vpcid)
    sgps = vpc_resource.security_groups.all()
    for sg in sgps:
        if sg.group_name == 'default':
            print(sg.id + " is the default security group, continue...")
            continue

        print("Removing all rules from sg-id: ", sg.id) if (VERBOSE == 1) else ""
        # Revoke all ingress rules
        try:
            sg.revoke_ingress(IpPermissions=sg.ip_permissions)
        except boto3.exceptions.Boto3Error as e:
            print(f"Error removing ingress rules from {sg.id}: {e}")

        # Revoke all egress rules
        try:
            sg.revoke_egress(IpPermissions=sg.ip_permissions_egress)
        except boto3.exceptions.Boto3Error as e:
            print(f"Error removing egress rules from {sg.id}: {e}")
    for sg in sgps:
        # Now delete the security group
        if sg.group_name == 'default':
            print(sg.id + " is the default security group, continue...")
            continue
        print("Deleting sg-id: ", sg.id) if (VERBOSE == 1) else ""
        try:
            sg.delete()
        except boto3.exceptions.Boto3Error as e:
            print(f"Error deleting security group {sg.id}: {e}")

def del_vpc(ec2, vpcid):
  """ Delete the VPC """
  vpc_resource = ec2.Vpc(vpcid)
  try:
    print("Removing vpc-id: ", vpc_resource.id)
    vpc_resource.delete(
      # DryRun=True
    )
  except boto3.exceptions.Boto3Error as e:
      print(e)
      print("Please remove dependencies and delete VPC manually.")
  #finally:
  #  return status

def del_vpc_all(ec2, vpc):
  """
  Do the work - order of operation

  1.) Delete the internet-gateway
  2.) Delete subnets
  3.) Delete route-tables
  4.) Delete network access-lists
  5.) Delete security-groups
  6.) Delete the VPC 
  """
  wait_for_alb_deletion(vpc)
  del_igw(ec2, vpc)
  del_sub(ec2, vpc)
  del_rtb(ec2, vpc)
  del_acl(ec2, vpc)
  del_sgp(ec2, vpc)
  del_vpc(ec2, vpc)



def wait_for_ec2_termination(ec2_resource, vpc_id):
    ec2_instances = ec2_resource.instances.filter(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    
    for instance in ec2_instances:
        instance.terminate()

    for instance in ec2_instances:
        instance.wait_until_terminated()

    print("ec2 instance(s) terminated")

def wait_for_rds_deletion(rds_client, vpc_id):
    rds_instances = rds_client.describe_db_instances()['DBInstances']
    rds_instances = [instance for instance in rds_instances if instance['DBSubnetGroup']['VpcId'] == vpc_id] #filter by vpc id
    for db_instance in rds_instances:
        if db_instance['DBSubnetGroup']['VpcId'] == vpc_id:
            rds_client.delete_db_instance(
                DBInstanceIdentifier=db_instance['DBInstanceIdentifier'],
                SkipFinalSnapshot=True)

    for db_instance in rds_instances:
        waiter = rds_client.get_waiter('db_instance_deleted')
        waiter.wait(DBInstanceIdentifier=db_instance['DBInstanceIdentifier'])
    print("RDS instance(s) deleted")

def wait_for_alb_deletion(vpc_id):
  elbv2_client = boto3.client('elbv2')
  load_balancers = [lb for lb in elbv2_client.describe_load_balancers()["LoadBalancers"] if lb["VpcId"] == vpc_id]
  for lb in load_balancers:
      print(lb["LoadBalancerName"], lb["LoadBalancerArn"])

      #delete listeners
      for li in elbv2_client.describe_listeners(LoadBalancerArn=lb["LoadBalancerArn"])["Listeners"]:
         print(f"Deleting listener : {li['ListenerArn']}")
         elbv2_client.delete_listener(ListenerArn=li["ListenerArn"])
      
      #delete target groups
      for t_group in elbv2_client.describe_target_groups(LoadBalancerArn=lb["LoadBalancerArn"])["TargetGroups"]:
        print(f'Deleting target group: {t_group["TargetGroupName"]}')
        #make deregistration delay 0
        elbv2_client.modify_target_group_attributes(
           TargetGroupArn=t_group["TargetGroupArn"],
           Attributes=[{'Key':'deregistration_delay.timeout_seconds', 'Value':'0'}]
        )
        #delete target group
        elbv2_client.delete_target_group(TargetGroupArn=t_group["TargetGroupArn"])

      #delete the application load balancer

      print("Waiting for load balancer to be deleted...")
      elbv2_client.delete_load_balancer(LoadBalancerArn=lb["LoadBalancerArn"])
      # Wait for the load balancer to be deleted
      while True:
          try:
              response = elbv2_client.describe_load_balancers(LoadBalancerArns=[lb["LoadBalancerArn"]])
              if not response['LoadBalancers']:
                  #print("Load Balancer deleted")
                  break
          except elbv2_client.exceptions.LoadBalancerNotFoundException:
              #print("Load Balancer deleted")
              break
          time.sleep(3)  # Wait for 10 seconds before checking again

      print(f'Load balancer deleted: {lb["LoadBalancerArn"]}')


      
    


def delete_infrastructure(vpc_id):
    print("Starting cleanup process - this can take a few minutes")
    ec2 = boto3.resource('ec2')
    rds_client = boto3.client('rds')

    # Create threads for termination
    ec2_thread = threading.Thread(target=wait_for_ec2_termination, args=(ec2, vpc_id,))
    rds_thread = threading.Thread(target=wait_for_rds_deletion, args=(rds_client, vpc_id,))
    # Start threads
    ec2_thread.start()
    rds_thread.start()
    # Wait for threads to complete
    ec2_thread.join()
    rds_thread.join()

    del_vpc_all(ec2, vpc_id)
    print("\nGreat success!")
   
#testing purposes:

if __name__ == '__main__':
   vpc_id = input("vpc_id:")
   if len(vpc_id) <10:
    vpc_id = "vpc-0be67a8712b032321"
   #delete_infrastructure(vpc_id)
   delete_infrastructure(vpc_id)


