## Requirements

* AWS CLI with Administrator permission
* [SAM Local installed](https://github.com/awslabs/aws-sam-local)

## Manual Deployment

1. Navigate to [AWS ECR](https://console.aws.amazon.com/ecr/get-started)
2. Create a new ECR repository
3. Build the docker image from the `src/main` directory by running `docker build -f AWSDockerfile -t pgplambda .`
4. Follow the instructions from the ECR repository `View Push Commands` button to tag and push the image to the ECR
   repository
6. Go to [AWS Lambda](https://console.aws.amazon.com/lambda/home)
7. Create a new Container image function
8. Browse to your ECR image and create
9. Once the function has been created, go to its configuration tab and set up
   the [environment variables](#lambda-environment-variables) bellow
10. Configure [permissions](#lambda-required-permissions) bellow on the lambda execution role

Now the PGP lambda should be fully operational, and you can configure the [S3 Event](#bucket-setup) to trigger the
lambda when a file is uploaded to the bucket.

## Cloud Formation Deployment

**_NOTE:_** This section is for the original AWS Lambda that used lambda layers and will be reworked soon.

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
DECRYPTED_DONE_LOCATION:
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
              - !Sub "arn:aws:s3:::<DECRYPTED_DONE_LOCATION>"
              - !Sub "arn:aws:s3:::<EncryptedSourceBucket>"
              - !Sub "arn:aws:s3:::<PGP_KEY_LOCATION>"
          - Effect: "Allow"
            Action:
              - "s3:PutObject"
              - "s3:GetObject"
              - "s3:DeleteObject"
            Resource:
              - !Sub "arn:aws:s3:::<DECRYPTED_DONE_LOCATION>/*"
              - !Sub "arn:aws:s3:::<EncryptedSourceBucket>/*"
              - !Sub "arn:aws:s3:::<PGP_KEY_LOCATION>/*"

    ```
