# PGP Decryption Lambda

## What is PGP Lambda

PGP Lambda is an automated post-processing decryption of PGP encrypted file that are uploaded to a source cloud storage
location in AWS, Azure, and GCP(WIP).

## How it works

When files are uploaded to the source cloud storage location an events is used to trigger the PGP lambda to pull in the
file, decrypt it, and place it into a done target cloud storage location.

# Instructions for Use and Deployment

## Requirements

* [Python 3.9 installed](https://www.python.org/downloads/)
* [Pipenv installed](https://github.com/pypa/pipenv)
    - `pip install pipenv`
* [AWS requirements](src/main/AWS/README.md#Requirements)
* [Azure requirements](src/main/Azure/README.md#Requirements)
* [GCP requirements](src/main/GCP/README.md#Requirements)


## Environment setup

1. run `pipenv install -r src/provider/requirements.txt`
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

## Shared Module
All cloud providers use the `src/main/res/` module and its contents for pgp decryption. Before deploying to any 
cloud provider you should copy the contents of the res directory into the provider specific res directory. 

# GPG Basics

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

  

  
