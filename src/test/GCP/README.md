# Testing the GCP PGP Lambda Locally
The PubSub Emulator can be used to test the PGP Lambda locally. The emulator cannot be accessed 
through the GCP console or the gcloud cli. The python script here are provided in order to interact with the 
emulator to set up topics, subscribers, and publish messages. These scripts were derived from the [Google APIs Python 
PubSub project](https://github.com/googleapis/python-pubsub)

For the full documentation on use the PubSub Emulator for local testing see the GCP 
[PubSub Emulator Docs][pubsub-emulator]

## Requirements 
* [Gcloud cli installed](https://cloud.google.com/sdk/docs/install)

## Install the Emulator
To install the GCP PubSub emulator run the command 
```shell
gcloud components install pubsub-emulator
gcloud components update
```

## Starting the Emulator
To start the emulator 
```shell
gcloud beta emulators pubsub start --project=PROJECT_ID --host-port=localhost:8085
```

Once the emulator is started you will get a message that the following message
```shell
[pubsub] This is the Pub/Sub fake.
[pubsub] Implementation may be incomplete or differ from the real system.
...
[pubsub] INFO: Server started, listening on 8085
```

## Interacting with the Emulator
Once the emulator is started you will need to use the scripts in this directory to create a topic, subscriber, and 
publish messages to the topic. All interactions with the PubSub emulator should be performed in the `src/test/GCP/` 
directory. In order for the scripts to connect with the Emulator you will need to set the environment variables. 

1. To set the environment variables run the command:
    ```shell
    $(gcloud beta emulators pubsub env-init)
    ```
    
1. Create a Topic
    ```shell
    python publisher.py PUBSUB_PROJECT_ID create TOPIC_ID
    ```
1. Create a push subscriber
    ```shell
    python subscriber.py PUBSUB_PROJECT_ID create-push TOPIC_ID SUBSCRIPTION_ID http://localhost:8080
    ```
1. Publish a Message
   
   The `publish_message` method in this script will publish a single message with an event taken from a production 
   PubSub topic. To get an event message follow the steps in the PGP Lambda GCP README for 
   [Configure PubSub Notifications for Cloud Storage](/src/main/GCP/README.md#configure-pubsub-notifications-for-cloud-storage)
   and 
   [Configure PubSub Subscriber to Trigger Cloud Run](/src/main/GCP/README.md#configure-pubsub-subscriber-to-trigger-cloud-run),
   but intead of configuring a push subscriber set up a pull subscriber. The when you upload a file to the Cloud 
   Storage bucket you can go into the pull subscriber and manually pull the message and get the event from the 
   message body. You can than paste that message body into the `event_message` variable of the `publish_message` method.
   ```shell
    python publisher.py PUBSUB_PROJECT_ID publish TOPIC_ID
   ```

## Running the Function Locally
Once you have the PubSub emulator setup and running you can run the PGP lambda locally to receive events from the 
emulator when a message is published. 

* Add a service account key file to the `src/main/GCP/` directory, with the permissions outlined in the
  [GCP Lambda README Service Account Permissions](/src/main/GCP/README.md#service-account-permissions)
* follow the steps in the [GCP Lambda README](/src/main/GCP/README.md#docker-deployment-to-cloud-run) to build the 
  docker image. 
* Instead of pushing the image up to the Artifact Registry, you can run the container locally. 
* Open port 8080 in the docker run command
* Add the environment variables described in the [Runtime Environment Variables](/README.md#runtime_environment_variables)
* Add an environment variable `GOOGLE_APPLICATION_CREDENTIALS` set to the name of the service account key file. 

Once the function is running in a local container you can use the Publish script to publish a message to the topic 
and the container will process the event. 

[pubsub-emulator]: https://cloud.google.com/pubsub/docs/emulator