import sys
import typer

from cloud_deployer.aws_functions import list_s3


app = typer.Typer()


@app.command()
def func():
    typer.echo(f"Hello World!")

@app.command()
def bye():
    typer.echo("bye")

@app.command()
def s3():
    try:
        list_s3()
    except:
        print("listing s3 buckets failed")

if __name__ == "__main__":
    app()
