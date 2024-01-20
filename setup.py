from setuptools import setup, find_packages

setup(
    name='cloud-deployer',
    version='0.1.0',
    author='Fateh Sadnhu',
    author_email='fatehss@g.ucla.edu',
    description='Cloud uploader',
    packages=find_packages(),
    install_requires=[
        "Typer[all]",
        "boto3",
        "aws",
        # List your project's dependencies here
        # e.g., 'requests', 'flask',
    ],
    entry_points={
        'console_scripts': [
            'cloud-deployer=cloud_deployer.main:func',
        ],
    },
)
