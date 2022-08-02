## Requirements

* [Gcloud cli installed](https://cloud.google.com/sdk/docs/install)

## Manual Deployment

This will outline the steps needed to create a zip packages and deploy it to GCP Cloud Functions.

1. Create the package zip by run the command `python3 deploy/GCP/make_zip.py` from the project root
2. In the [Google Function Console](https://console.cloud.google.com/functions/list), create a new function
3. Leave the environment as `1st gen`, give the function a name, and select a desired region
4. Change the Trigger type to `Cloud Storage` and select event type `finalizing/create`
5. Choose a source bucket where your encrypted files will be located and save the trigger
6. Under the Runtime sections, allocated 2GB of memory and leave the timeout at 60
7. Under Runtime Service Account, create a new service account, then add the permissions listed
   in [Service Account Permissions](#service_account_permissions)
8. Add the environment variables as defined in
   the [Environment Variables section](/README.md#runtime_environment_variables)
9. Then hit next to go to the code section
10. In the runtime selector, choose `Python 3.9`
11. In the source code selector, choose `ZIP Upload`
12. Set the Entry Point to `invoke`
13. Browse to the `depoy/GCP/pgpGoogleArchive.zip`
14. Set a staging bucket for the zip file to be deployed from
15. Finally, hit Deploy

Once the functions is finished deploying any encrypted file uploaded to the trigger bucket will automatically be 
decrypted and placed into the done bucket.

## Service Account Permissions

* Cloud Storage Viewer
* Cloud Storage Creator
