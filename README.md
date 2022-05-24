# PGP Lambda

## Requirements

* AWS CLI with Administrator permission
* [Python 3.9 installed](https://www.python.org/downloads/)
* [Pipenv installed](https://github.com/pypa/pipenv)
    - `pip install pipenv`
* [SAM Local installed](https://github.com/awslabs/aws-sam-local)

## Environment setup

1. run `pipenv install -r src/requirements.txt`
2. run `pipenv lock && pipenv sync`

## Updating python version

1. Update `required:python_version` in Pipfile to "3.9"
2. run `pipenv install --python=python3.9`

## Updating dependencies

### To unpin dependencies and allow them to be updated

1. modify dependency version in pipfile from `==x.x.x` to `>=x.x.x`
2. run `pipenv update`

### To pin dependencies into a non-updatable state

1. run `pipenv run freeze > src/requirements.txt`
2. run `pipenv install -r src/requriement.txt`

### GNUPG Dependencies

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

## Keys

PGP uses a public private key pair for encrypting and decrypting file.

To generate a new PGP key on Mac, use the following command:

```shell script
gpg --gen-key
```

This will open an interactive generation script that will ask you a number of questions.

To export a public key for use in the encryption process use the command:

```shell script
gpg --export -a username > public.key
```

Once a public key is sent to the user they will have to import that key into their GPG keyring

To import a public key use the command:

```shell script
gpg --import public.key
```

An ASC file is an Armored ASCII file that is generated as plain ASCII text.

To create an ASC file to be used in the decryption process use the command:

```shell script
gpg --export-secret-key -a username > private.asc
```

## Encryption

The file will be encrypted by the sending user with the receiving user's public key.

To encrypt a file use the command:

```shell script
gpg -e -u "sender_username" -r "receiver_username" file_to_be_encrypted
```

## Decryption

When the file arrives in the S3 bucket, a put event is triggered if the file has a `.gpg` or `.pgp` extension. The
event will fire the pgplambda that will download a temporary copy of the file from the file bucket and the key from the
key bucket, decrypt the file, and move it to a ready folder inside of S3.

Manually decrypt data

```shell script
gpg -d filename.extension.gpg
``` 

## Deployment

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
LOG_LEVEL: [ CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET ]
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
* Policy for access to file bucket
    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "VisualEditor0",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:DeleteObject"
                ],
                "Resource": [
                    "arn:aws:s3:::<file-bucket>",
                    "arn:aws:s3:::<file-bucket>/*"
                ]
            }
        ]
    }
    ```
* Policy for access to key bucket
    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "VisualEditor0",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::<pgp-key-bucket>",
                    "arn:aws:s3:::<pgp-key-bucket>/*"
                ]
            }
        ]
    }
    ```
  
  
