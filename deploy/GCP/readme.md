python3 deploy/GCP/make_zip.py
mv deploy/GCP/pgpGoogleArchive.zip ~/Downloads/pgpGoogleArchive.zip


gcloud config set project sftp-gateway
gcloud deployment-manager deployments create {NAME} --config pgp_addon.yaml