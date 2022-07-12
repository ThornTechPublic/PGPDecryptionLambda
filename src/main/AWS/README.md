## Requirements

* AWS CLI with Administrator permission
* [SAM Local installed](https://github.com/awslabs/aws-sam-local)

### GNUPG Dependencies

**_NOTE:_** This section is for the orignial AWS Lambda that used lambda layers and will be depricated upon
completion of the containerized AWS image.

The GNUPG dependencies are contained in the `dependencies/` directory, and will be deployed to a lambda layer.
These dependencies where created by using the Dockerfile to provision a container with Python3.9.
You can then connect to the container and `cd /opt`. Then create a directory called `layer/` with the following
sub-directories `bin`, `lib`, and `python`. You can then install the GNUPG dependencies into the `layer/python/`
directory with the command `pip install gnupg -t ./layer/python`. The GNUPG module requires an installed GPG binary and
its subsequent dependencies. This was accomplished by creating a directory `mkdir -p /opt/tmppackages/etc` then copying
all of the Yum commands to that `tmppackages/etc` directory with `cp -r /etc/yum* /opt/tmppackages/etc/` this allows
the use of the yum install root option. Then using the command
`yum install -y --installroot=/opt/tmppackages --releasever=/ gpg` to install gpg and its dependencies
to the `/opt/tmppackages` directory which will create a `bin`, `lib`, and `lib64` directories. The GPG binaries can then
be copies over to the `layer/bin/` directory with the command `cp -r /opt/tmppackages/bin/gpg* /opt/layer/bin/`. The GPG
dependencies can be aquired with the command
`ldd /opt/tmppackages/bin/gpg | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /opt/layer/lib/`
Now all of the dependencies for GNUPG and the GPG binary can be packaged by `cd /opt/layer` and run the command
`zip -r ../layer.zip .`. the zip file can then be obtained from the container with the command
`docker cp <containerName>:/opt/layer.zip local/path`, and extracted into the `<project_root>/dependencies` directory.

## Manual Deployment

1. Navigate to [AWS ECR](https://console.aws.amazon.com/ecr/get-started)
2. Create a new ECR repository
3. Follow the instruction in the View Push Commands modal
4. Build the docker image
5. Push the docker image to the ECR repo
6. Go to [AWS Lambda](https://console.aws.amazon.com/lambda/home)
7. Create a new Container image function
8. Browse to your ECR image and create
9. Once the function has been created, go to its configuration tab and set up the [environment variables](#lambda-environment-variables) bellow
10. Configure [permissions bellow](#lambda-required-permissions) on the lambda execution role


Using the SAM CLI deploy the template.yaml file.

### Template Parameters

```yaml
PgpKeyLocation:
    Type: String
    Description: "S3 bucket where the PGP private key is located"
PgpKeyName:
    Type: String
    Description: "Name of the PGP private key"
DecryptedTargetBucket:
    Type: String
    Description: "S3 Bucket where files will land lambda decryption"
EncryptedSourceBucket:
    Type: String
    Description: "S3 Bucket that triggers lambda to decrypt files. Needed for permissions"
```

### Lambda Environment Variables

```yaml
LOG_LEVEL:
    Allowed Values: [ CRITICAL | ERROR | WARNING | INFO | DEBUG | NOTSET ]
    Description: "(Optional) Set log level if desired."
    Default: INFO
    Type: String
PGP_PASSPHRASE:
    Type: String
    Description: "(Optional) Set PGP Key passphrase if applicable "
    Default: None
PGP_KEY_LOCATION:
    Type: String
    Description: "S3 bucket where the PGP private key is located"
PGP_KEY_NAME:
    Type: String
    Description: "Name of the PGP private key"
DECRYPTED_DONE_BUCKET:
    Type: String
    Description: "S3 Bucket where files will land lambda decryption"
ARCHIVE:
    Type: Boolean
    Default: false
    Descritption: "(Optional) If true, files that have already been decrypted will be moved into an archive folder in the source bucket"
ERROR:
    Type: Boolean
    Default: false
    Descritption: "(Optional) If true, files that encounter an error will decrypting will be moved into an error folder in the source bucket"
```

## Bucket setup

1. In the S3 console, go to the SFTP Gateway default bucket
1. In the properties tab, open the Events section
1. Click Add notification
1. Name the notification `gpg-file-uploaded`, select Event `PUT`, enter the `.gpg` Suffix, select Send to Lambda
   Funcation, and select the pgp-file-decrypter-PgpLambda
1. Repeat previous step for `.pgp` files

## Lambda required permissions

The pgp lambda will require the following permissions to create log streams in CloudWatch and acess the file and key
buckets.

* AWSLambdaBasicExecutionRole
* Policy listing bucket and accessing file objects in those buckets
    ```yaml
    Policies:
      - Version: "2012-10-17"
        Statement:
          - Effect: "Allow"
            Action:
              - "s3:ListBucket"
            Resource:
              - !Sub "arn:aws:s3:::${DecryptedTargetBucket}"
              - !Sub "arn:aws:s3:::${EncryptedSourceBucket}"
              - !Sub "arn:aws:s3:::${PgpKeyLocation}"
          - Effect: "Allow"
            Action:
              - "s3:PutObject"
              - "s3:GetObject"
              - "s3:DeleteObject"
            Resource:
              - !Sub "arn:aws:s3:::${DecryptedTargetBucket}/*"
              - !Sub "arn:aws:s3:::${EncryptedSourceBucket}/*"
              - !Sub "arn:aws:s3:::${PgpKeyLocation}/*"

    ```
