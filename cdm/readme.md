get sftpgw-pgp-lambda/cdm/pgpGoogleArchive.zip

gcloud config set project sftp-gateway
gcloud deployment-manager deployments create {NAME} --config pgp_addon.yaml