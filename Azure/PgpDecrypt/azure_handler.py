from res.sharedconstants import *
from res.pgpDecrypt import process_files

import os
import sys
import traceback
from os.path import join, isfile
from urllib import parse

import azure.storage.blob
import azure.functions
import azure.identity

# TODO test (normal, multiple files, files in folders, key in folders, zip folders, nested zip folders)
# TODO replace s3's with azure at end (comments and strings too)


def move_on_az(dest_container, account_url, container, filepath):
    dest_blob_obj = azure.storage.blob.BlobClient.from_connection_string(CONNECTION_STRING, dest_container, filepath)
    source_url = '/'.join([account_url, container, filepath])
    logger.info(f'moving original file to {dest_container} container')
    dest_blob_obj.start_copy_from_url(source_url, requires_sync=True)
    source_blob_obj = azure.storage.blob.BlobClient.from_connection_string(CONNECTION_STRING, container, filepath)
    logger.info('deleting original upload blob')
    source_blob_obj.delete_blob()


def download_file_on_az(container: str, filepath: str):
    blob_obj = azure.storage.blob.BlobClient.from_connection_string(CONNECTION_STRING, container, filepath)
    logger.info(f'downloading to {filepath}')
    # try:
    with open(join(DOWNLOAD_DIR, filepath), "wb") as f:
        blob_obj.download_blob().readinto(f)
    exists = True
    # except ClientError as e:
    #     error_code = int(e.response['Error']['Code'])
    #     if error_code == 404:
    #         exists = False
    #         logger.warning(
    #             'attempt to download s3://{0}/{1} failed, it was not found. Most likely file was already processed.'.format(
    #                 bucket, key))
    #     else:
    #         raise e
    return exists


# download the private encryption key from azure
def download_asc_on_az():
    logger.info(f'Attempting to download key from Azure: {PGP_KEY_LOCATION}/{ASC_REMOTE_KEY}')
    blob_obj = azure.storage.blob.BlobClient.from_connection_string(CONNECTION_STRING, PGP_KEY_LOCATION, ASC_REMOTE_KEY)
    # Disable logging of key data while importing the key
    key_data = blob_obj.download_blob().readall()
    if isinstance(key_data, bytes):
        logger.warn("Alert: Key data returned as bytes! Decoding now...")
        key_data = key_data.decode("UTF-8")
    import_result = gpg.import_keys(key_data)
    logger.info('key import result fingerprint: {}'.format(', '.join(import_result.fingerprints)))


def copy_files_on_az(copy_source_dir: str, container: str, prefix: str):
    for f in os.listdir(copy_source_dir):
        local_filepath = join(copy_source_dir, f)
        if isfile(local_filepath):
            remote_filepath = join(prefix, f)
            logger.info(f'Uploading: {local_filepath} to {remote_filepath}')
            with open(local_filepath, "rb") as file:
                azure.storage.blob.BlobClient.from_connection_string(CONNECTION_STRING, container,
                                                                     remote_filepath).upload_blob(file)


# Store file in error directory
def error_on_az(container, filepath):
    if ERROR:
        move_on_az('error', container, filepath)


# Archive and delete the file
def archive_on_az(container, filepath):
    if ARCHIVE:
        move_on_az('archive', container, filepath)


def invoke(event: azure.functions.InputStream):
    logger.info(f"New event: {event}")
    url = event.uri
    url = parse.unquote_plus(url)
    blob_obj = azure.storage.blob.BlobClient.from_blob_url(url)
    container_name = blob_obj.container_name
    filepath = blob_obj.blob_name
    logger.debug(f'Azure Event: {container_name}/{filepath} was uploaded')
    prefix = trim_path_to_directory(filepath)

    if not filepath.endswith(('.pgp', '.gpg')):
        logger.info(f'File {filepath} is not an encrypted file... Skipping')
    elif ARCHIVE and prefix.startswith('archive'):
        logger.debug('Archive event triggered... Skipping')
    elif ERROR and prefix.startswith('error'):
        logger.debug('Error event triggered... Skipping')
    else:
        try:
            reset_folder(DOWNLOAD_DIR)
            reset_folder(DECRYPT_DIR)
            reset_folder(LOCAL_UNZIPPED_DIR)
            reset_folder(LOCAL_READY_DIR)
            logger.info(f'Begin Processing {url}')

            # TODO figure out equivalent
            # if int(record['s3']['object']['size']) == 0:
            #     logger.info('File {key} is a placeholder file... Skipping'.format(key=key))
            #     continue

            file_exists = download_file_on_az(container_name, filepath)

            if file_exists:
                download_asc_on_az()
                # process until download_dir is empty
                process_files()
                # copy ready files to s3 ready bucket
                logger.info('Uploading files')
                copy_files_on_az(LOCAL_READY_DIR, DECRYPTED_DONE_LOCATION, prefix)
                archive_on_az(container_name, filepath)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            message = f'Unexpected error while processing upload {container_name}/{filepath}, with message \"{exc_value}\". \
                      The file has been moved to the error folder. Stack trace follows: {"".join("!! " + line for line in lines)}'
            logger.error(message)
            error_on_az(container_name, filepath)
