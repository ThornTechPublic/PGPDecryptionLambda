import argparse
import os

import boto3

# Global variables
PROJECT = 'pgp-file-decrypter'
BUCKET = 'pgp-lambda-deploy'


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

def deploy(project, profile, params):
    # the actual deployment step
    os.system('sam deploy                         \
        --template-file build/output.yaml         \
        --stack-name {project}                    \
        --capabilities CAPABILITY_NAMED_IAM       \
        --profile {profile}                       \
        --parameter-overrides {params}'.format(
        project=project,
        profile=profile,
        params=' '.join(params)
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
    parser.add_argument(
        '--deploy-bucket',
        '-d',
        help='Specify S3 bucket to user for SAM deployment',
        type=str,
        default=BUCKET
    )
    parser.add_argument(
        '--template-params',
        '-t',
        help='List template parameters as \
        `PgpKeyLocation=value PgpKeyName=value DecryptedTargetBucket=value EncryptedSourceBucket=value`',
        nargs='+',
        type=str,
        action='extend'
    )
    return parser.parse_args(args)


def clean_build(target):
    if os.path.exists(target):
        for d in os.listdir(target):
            try:
                clean_build('{}/{}'.format(target, d))
            except OSError:
                os.remove('{}/{}'.format(target, d))
        os.rmdir(target)


def main(args=None):
    args = parse_args(args)
    profile = args.profile
    bucket = args.deploy_bucket
    params = args.template_params

    # Create the deployment bucket if it does not exist
    create_deployment_bucket(bucket, profile)

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
    deploy(PROJECT, profile, params)
    print('Deployment complete.')


if __name__ == "__main__":
    main()
