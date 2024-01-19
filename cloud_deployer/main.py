import sys
import argparse

#handles argparse for the cli tool

parser = argparse.ArgumentParser(
    prog='cloud deployer',
    description='deploys cloud infrastructure',
    epilog='bottom text'
)
parser.add_argument('number', type=int, help='an integer number')


def func():
    args = parser.parse_args()
    print(args.number*2)
