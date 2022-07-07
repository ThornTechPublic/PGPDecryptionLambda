# PGP Decrypted Lambda for Azure

## Requirements

* [az cli installed](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
* [azure-functions-core-tools@4 installed](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=v4%2Clinux%2Ccsharp%2Cportal%2Cbash)

## Deployment

This documentation is a reflection of the [Azure Function on Linux with Custom Container](https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-function-linux-custom-image?tabs=in-process%2Cbash%2Cazure-cli&pivots=programming-language-python)

1. create docker image
2. publish docker image
3. create resource group

```shell
az group create \
    --name <RESOURCE_GROUP_NAME> \
    --location <REGION>
```

4. create storage account

```shell
az storage account create \
    --name <STORAGE_NAME> \
    --location <REGION> \
    --resource-group <RESOURCE_GROUP_NAME> \
    --sku Standard_LRS
```

5. create host plan

```shell
az functionapp plan create \
    --resource-group <RESOURCE_GROUP_NAME> \
    --name <HOST_PLAN_NAME> \
    --location <REGION> \
    --number-of-workers 1 \
    --sku EP1 \
    --is-linux
```

6. create function app

```shell
az functionapp create \
    --name <APP_NAME> \
    --storage-account <STORAGE_NAME> \
    --resource-group <RESOURCE_GROUP_NAME> \
    --plan <HOST_PLAN_NAME> \
    --deployment-container-image-name <DOCKER_ID>/azurefunctionsimage:v1.0.0
```

7. configure function app settings

```shell
az functionapp config appsettings set \
    --name <APP_NAME> \
    --resource-group <RESOURCE_GROUP_NAME> \
    --settings \
      AzureWebJobsStorage=<Connection string from storage account created in step 4> \
      AZURE_STORAGE_CONNECTION_STRING=<Connection string for storage account that houses pre-processing, post-processing, and pgp-key containers> \
      ENCRYPTED_SOURCE_BUCKET=<Container where GPG encrypted files will be uploaded for processing> \
      DECRYPTED_DONE_LOCATION=<Container where files will be sent after processing> \
      PGP_KEY_LOCATION=<Container where PGP key file is stored> \
      PGP_KEY_NAME=<Name of PGP ASC key file> \
      PGP_PASSPHRASE=<(optional) passphrase for pgp key file if applicable > 
```
