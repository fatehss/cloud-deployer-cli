from setuptools import setup, find_packages

setup(
    name='cloud-deployer',
    version='0.1.1',
    author='Fateh Sandhu',
    author_email='fatehss@g.ucla.edu',
    description='Cloud uploader',
    packages=find_packages(),
    install_requires=[
        "Typer[all]",
        "boto3",
        # List your project's dependencies here
        # e.g., 'requests', 'flask',
    ],
    entry_points={
        'console_scripts': [
            'cloud-deployer=cloud_deployer.main:app',
        ],
    },
)
