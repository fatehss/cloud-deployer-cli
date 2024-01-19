import argparse
import sys

#this module will handle the aws config setup for argparse

def config_user():
#will store the credentials of aws cli in the 
    aws_id = input("Enter AWS ID")
    if not aws_id:
        print("aws_id cannot be blank")
    region = input ("Enter Region:")
    #todo: finish this function