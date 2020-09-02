# PGP Lambda 

## Requirements
* AWS CLI with Administrator permission
* [Python 3.6 installed](https://www.python.org/downloads/)
* [Pipenv installed](https://github.com/pypa/pipenv)
    - `pip install pipenv`
* [Docker installed](https://www.docker.com/community-edition)
* [SAM Local installed](https://github.com/awslabs/aws-sam-local) 


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

To create a ASC file to be used in the decryption process use the command:
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
1. Install dependencies
    `pipenv install `
1. Run the deploy.py script
    `pipenv run python deploy.py [-p | --profile <AWS_PROFILE>]`
    
    
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
  
  
