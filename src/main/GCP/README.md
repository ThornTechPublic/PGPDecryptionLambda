## Requirements

* [Gcloud cli installed](https://cloud.google.com/sdk/docs/install)
* [PubSub topic](https://console.cloud.google.com/cloudpubsub/topic/list)
* [Artifact Registry](https://console.cloud.google.com/artifacts)


## Pre-requisit
In order to build and deploy docker images to Google Cloud Run, you need to have a Google Artifact Registry setup.

* Go to the [Google Artifact Registry](https://console.cloud.google.com/artifacts)
* Select the Google project you with to deploy to 
* Create a new Repository and give it a name
* Select the Docker format
* Select a location type, and Region 
* Click Create

Once this repository has been created you can navigate into the repo. Just under the title "Images for [repo_name]", 
there will be a folder breadcrumb with a copy button next to it. This is the Artifact Repository address that 
will be used for the start of the image tag you will need to use to create the docker image in the next section.

## Docker Deployment to Cloud Run
This section will cover building the PGP decryption lambda with docker, publishing the image to Google Artifact 
Registry, and deploying that Artifact Image to Google Cloud Run. 

* From the `src/main/` directory, build the docker file. Copy the Google Artifact Repository address, then this into 
  the build command and add an image label 
    ```shell
    docker build --file GoogleDockerfile --tag <artifact_region>-docker.pkg.dev/<project_id>/<artifact_repo_name>/<image_label> .
    ```
    **Note:** it is important to add the period at the end of the command to specify that this command is to be run 
  in the current directory

* (First time Setup): The Artifact registry needs to be configured in the docker cli. In the artifact repository there 
  is a button that 
  says `Setup Instructions`. This will open a small panel on the side with a command that can be copied and pasted 
  into your terminal. This only has to be done first time you push an image to the artifact repository. 

* Push the image to artifact registry 
  ```shell
  docker push <artifact_region>-docker.pkg.dev/<project_id>/<artifact_repo_name>/<image_label>
  ```
* From the artifact registry repo, click on the latest version of the image and click deploy to Cloud Run. This will 
  bring you to the Cloud Run configuration screen and fill in the image URL.
* The name will automatically be filled in as the name of the image. You can change this or leave it as is.
* In the Authentication section, check the "require authentication" option
* Expand the Container Connections Security section
* On the Container tab se the memory to 2 GiB
* In the Environment Variables section, Configure the [Environment Variables](/README.md#runtime_environment_variables) 
  defined in the project root readme.
* On the Security tab, Select a service account with the permissions defined in the 
  [Service Account Permissions](#service-account-permissions) section
* Click Deploy 

## Configure PubSub notifications for Cloud Storage
The steps for configuring the notification event for Cloud Storage can be found in this 
[GCP documentation](https://cloud.google.com/storage/docs/reporting-changes#command-line)

## Configure PubSub Subscriber to Trigger Cloud Run
This section will cover how to configure a Google PubSub topic subscriber to push event triggers to the Cloud Run 
service. For this process you will need a deployed Cloud Run service. 

Get the Cloud Run Service invocation URL 
* Open the Cloud Run service
* Next to the Name of the service will be a URL with a copy button next to it.
* Copy this URL and continue to the next steps

Setup PubSub Subscriber
* In the PubSub topic, create a new subscriber, or edit the default subscriber.
* Set a subscriber ID
* Set delivery type to "Push"
* Paste the service invocation URL retrieved in the last step
* Check the "Enable Authentication" box
* Select a service account with permissions defined in the 
  [Service Account Permissions](#service-account-permissions) section
* Set the Acknowledgement Deadline to 600 seconds
* Click create

Once this subscriber is set up, event messages from Cloud Storage will be pushed to the Cloud Run service for 
processing. 

## Service Account Permissions

Cloud Run Service account without Archive or Error
* Cloud Storage Viewer
* Cloud Storage Creator

Cloud Run Service Account with Archive or Error
* Cloud Storage Admin

PubSub Subscriber
* Cloud Run Invoker
