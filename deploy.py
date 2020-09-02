import argparse
import boto3
import os

# Global variables
PROJECT = 'pgp-file-decrypter'
BUCKET = 'pgp-lambda-code'


def create_deployment_bucket(bucket, profile):
    session = boto3.Session(profile_name=profile)
    s3 = session.client('s3')
    response = s3.create_bucket(Bucket=bucket)
    return response


def build():
    # Build the Lambda deployment packages
    os.system('sam build -b build/')


def package(bucket, profile):
    # generate next stage yaml file
    os.system('sam package                       \
        --template-file build/template.yaml      \
        --output-template-file build/output.yaml \
        --s3-bucket {bucket}                     \
        --profile {profile}'.format(bucket=bucket, profile=profile)
              )


def deploy(project, profile):
    # the actual deployment step
    os.system('sam deploy                         \
        --template-file build/output.yaml         \
        --stack-name {project}                    \
        --capabilities CAPABILITY_NAMED_IAM       \
        --profile {profile}'.format(
        project=project,
        profile=profile,
    )
    )


def parse_args(args=None):
    des = "Deploys the pgp decryption lambda"
    parser = argparse.ArgumentParser(description=des)
    parser.add_argument(
        '--profile',
        '-p',
        help="Specify an AWS profile",
        type=str,
        default='default'
    )
    return parser.parse_args(args)


def clean_build(target):
    for d in os.listdir(target):
        try:
            clean_build('{}/{}'.format(target, d))
        except OSError:
            os.remove('{}/{}'.format(target, d))
    os.rmdir(target)


def main(args=None):
    args = parse_args(args)
    profile = args.profile

    # Create the deployment bucket if it does not exist
    create_deployment_bucket(BUCKET, profile)

    # Clean and recreate the build directory
    clean_build('build')
    os.mkdir('build')

    print('Building...')
    build()
    print('Build complete...')

    print('Packaging...')
    package(BUCKET, profile)
    print('Packaging complete...')

    print('Deploying...')
    deploy(PROJECT, profile)
    print('Deployment complete.')


if __name__ == "__main__":
    main()
