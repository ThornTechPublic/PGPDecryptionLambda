# BlobTrigger - Python

The `BlobTrigger` makes it incredibly easy to react to new Blobs inside of Azure Blob Storage. This sample demonstrates a simple use case of processing data from a given Blob using Python.

## How it works

For a `BlobTrigger` to work, you provide a path which dictates where the blobs are located inside your container, and can also help restrict the types of blobs you wish to return. For instance, you can set the path to `samples/{name}.png` to restrict the trigger to only the samples path and only blobs with ".png" at the end of their name.

## Learn more

<TODO> Documentation </TODO>

## Local testing on a remote machine

* Start an ec2 instance of Ubuntu 20.04 (the username is ubuntu not ec2-user)
* SSH in
* Download git, docker, and azure function core tools
* Git clone the pgp repo
* Optional install python 3.9 and pipenv and set project interpreter to it
* Connect through Jetbrains Gateway (NOT EAP version)
* Do docker login on terminal
* Set up IntelliJ service to run docker build (make sure to specify env vars in the edit config menu)
* At this point make sure your function.json "connection" value is set to the same name as the connection string's env var
  * Also, the "path" value should look something like %ENCRYPTED_SOURCE_BUCKET%/{name}
* Run service to build docker image
* Do docker run or use the IntelliJ service to run the docker image

## Upload image to Azure function

* Push docker image to docker hub
* Make a Function App in Azure portal
  * Make sure to select Docker container and linux in the instance details
* Enter your new function app and click on Deployment Center in Deployment section
  * Specify the source as Docker Hub, give it the image tag, and (might be optional?) click yes on continuous deployment
* Click on Configuration and press New application setting for each env var you need to add
  * you do not need to add AzureWebJobsStorage or FUNCTIONS_WORKER_RUNTIME
* Click App Service Logs under monitoring
  * Select File System and specify a quota and retention period
* The function should now be ready, click on Functions and click on the only item in the list
  * You can click Monitor then Logs to see the logs of your function (assuming you did the prior step)
  * You can click on Code + Test to see the contents of some code files (but not change them)
  * You can click on integration to see the trigger of this function (that info comes from function.json)
* Note that functions from images cannot be edited in the Azure portal so all changes will have to be made on your local machine then pushed to docker hub

## Other Notes

* On Azure, each file uploaded is run in its own function for the BlobTrigger.
  * However, these may be on the same machine instance so the code must be essentially race-free for OS functions