from res.sharedconstants import *
from res.pgpDecrypt import process_file

import os
import sys
import traceback
from os.path import join, isfile
from urllib import parse
import tempfile

import azure.storage.blob
import azure.functions
import azure.identity


# Fails if blob should not be in the account url or if the account name contains a ;
def move_on_az(dest_folder: str, container: str, remote_filepath: str):
    dest_blob_name = timestamp_filename(join(dest_folder, remote_filepath))
    dest_blob_obj = azure.storage.blob.BlobClient.from_connection_string(CONNECTION_STRING, container, dest_blob_name)
    logger.info(f'moving {remote_filepath} to {dest_blob_obj.blob_name}')
    source_blob_obj = azure.storage.blob.BlobClient.from_connection_string(CONNECTION_STRING,
                                                                           container, remote_filepath)
    with tempfile.TemporaryFile(mode="w+b") as f:
        source_blob_obj.download_blob().readinto(f)
        f.seek(0)
        dest_blob_obj.upload_blob(f)
    logger.info('deleting original upload blob')
    source_blob_obj.delete_blob()


def download_file_on_az(container: str, remote_filepath: str):
    blob_obj = azure.storage.blob.BlobClient.from_connection_string(CONNECTION_STRING, container, remote_filepath)
    download_filepath = join(DOWNLOAD_DIR, randomize_filename(trim_path_to_filename(remote_filepath)))
    logger.info(f'downloading to {download_filepath}')
    with open(download_filepath, "wb") as f:
        blob_obj.download_blob().readinto(f)
    return download_filepath


# download the private encryption key from azure
def download_asc_on_az():
    logger.info(f'Attempting to download key from Azure: {PGP_KEY_LOCATION}/{ASC_REMOTE_KEY}')
    blob_obj = azure.storage.blob.BlobClient.from_connection_string(CONNECTION_STRING, PGP_KEY_LOCATION, ASC_REMOTE_KEY)
    # Disable logging of key data while importing the key
    key_data = blob_obj.download_blob().readall()
    if isinstance(key_data, bytes):
        key_data = key_data.decode("UTF-8")
    import_result = gpg.import_keys(key_data)
    logger.info(f'key import result fingerprint: {", ".join(import_result.fingerprints)}')


def copy_file_on_az(local_filepath: str, container: str, remote_filepath: str):
    if isfile(local_filepath):
        logger.info(f'Uploading: {local_filepath} to {remote_filepath}')
        with open(local_filepath, "rb") as f:
            blob_obj = azure.storage.blob.BlobClient.from_connection_string(
                CONNECTION_STRING, container, remote_filepath)
            if blob_obj.exists():
                logger.info("Attempting to replace existing blob")
                blob_obj.delete_blob()
            blob_obj.upload_blob(f)


# Store file in error directory
def error_on_az(container: str, filepath: str):
    if ERROR:
        move_on_az('error/', container, filepath)


# Archive and delete the file
def archive_on_az(container: str, filepath: str):
    if ARCHIVE:
        move_on_az('archive/', container, filepath)


def invoke(event: azure.functions.InputStream):
    logger.info(f"New event: {event}")
    url = event.uri
    url = parse.unquote_plus(url)
    blob_obj = azure.storage.blob.BlobClient.from_blob_url(url)
    container_name = blob_obj.container_name
    remote_filepath = blob_obj.blob_name
    logger.info(f'Azure Event: {container_name}/{remote_filepath} was uploaded')

    if not remote_filepath.endswith(('.pgp', '.gpg', '.zip')):
        logger.info(f'File {remote_filepath} is not an encrypted file... Skipping')
    elif ARCHIVE and remote_filepath.startswith('archive/'):
        logger.info('Archive event triggered... Skipping')
    elif ERROR and remote_filepath.startswith('error/'):
        logger.info('Error event triggered... Skipping')
    else:
        try:
            logger.info(f'Begin Processing {url}')

            local_filepath = download_file_on_az(container_name, remote_filepath)
            download_asc_on_az()
            local_filepath = process_file(local_filepath)
            # copy file to azure container
            logger.info(f'Uploading file {local_filepath}')
            dest_remote_filepath = os.path.splitext(remote_filepath)[0]
            copy_file_on_az(local_filepath, DECRYPTED_DONE_LOCATION, dest_remote_filepath)
            archive_on_az(container_name, remote_filepath)
            os.remove(local_filepath)
        except Exception as ex:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            message = f'Unexpected error while processing upload {container_name}/{remote_filepath}, with message \"{exc_value}\". \
                      The file has been moved to the error folder. Stack trace follows: {"".join("!! " + line for line in lines)}'
            logger.error(message)
            error_on_az(container_name, remote_filepath)
            raise ex
