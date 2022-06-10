from sharedconstants import *
from pgplambda import process_files

import logging
import os
import sys
import traceback
from os.path import join, isfile
from urllib import parse

import azure.storage.blob
import azure.functions
import azure.identity
credentials = azure.identity.DefaultAzureCredential()

# TODO test (normal, multiple files, files in folders, key in folders, zip folders, nested zip folders)
# TODO replace s3's with azure at end (comments and strings too)

def move_on_az(dest_folder, bucket, key):
    # TODO translate
    download_filename = trim_path_to_filename(key)
    new_key = join(dest_folder, download_filename)
    logger.info('move original file to ' + new_key)
    S3.Object(bucket, new_key).copy_from(CopySource='{0}/{1}'.format(bucket, key))
    logger.info('deleting original upload file')
    S3.Object(bucket, key).delete()


def download_file_on_az(url: str, download_path=None):
    blob_obj = azure.storage.blob.BlobClient.from_blob_url(url, credentials)
    if download_path is None:
        download_path = blob_obj.blob_name
    logger.info(f'downloading {url} to {download_path}')
    # try:
    with open(join(DOWNLOAD_DIR, download_path), "wb") as f:
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
def download_asc_on_az(account_url: str):
    logger.info(f'Attempting to download key from Azure: {PGP_KEY_LOCATION}/{ASC_REMOTE_KEY}')
    blob_obj = azure.storage.blob.BlobClient(account_url, PGP_KEY_LOCATION, ASC_REMOTE_KEY, credential=credentials)
    # Disable logging of key data while importing the key
    key_data = blob_obj.download_blob().readall()
    if isinstance(key_data, bytes):
        logger.warn("Alert: Key data returned as bytes! Decoding now...")
        key_data = key_data.decode("UTF-8")
    import_result = gpg.import_keys(key_data)
    logger.info('key import result fingerprint: {}'.format(', '.join(import_result.fingerprints)))


def copy_files_on_az(copy_source_dir: str, account_url: str, container: str, prefix: str):
    for f in os.listdir(copy_source_dir):
        local_filepath = join(copy_source_dir, f)
        if isfile(local_filepath):
            remote_filepath = join(prefix, f)
            logger.info(f'Uploading: {local_filepath} to {remote_filepath}')
            with open(local_filepath, "rb") as file:
                azure.storage.blob.BlobClient(account_url, container, remote_filepath,
                                              credential=credentials).upload_blob(file)


# Filepath here is the full path including folders and the filename (and extension) of the remote file
# Store file in error directory
def error_on_az(bucket, filepath):
    # TODO translate
    if ERROR:
        move_on_az('error/', bucket, filepath)


# Archive and delete the file
def archive_on_az(bucket, filepath):
    # TODO translate
    if ARCHIVE:
        move_on_az('archive/', bucket, filepath)


def invoke(event: azure.functions.EventGridEvent):
    print(event.get_json())
    url = event.get_json()["data"]["url"]
    #url = parse.unquote_plus(url)
    account_url = url.rsplit('/', url.count('/')-2)
    blob_obj = azure.storage.blob.BlobClient.from_blob_url(url, credentials)
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

            download_path = join(DOWNLOAD_DIR, trim_path_to_filename(filepath))
            file_exists = download_file_on_az(url, download_path)

            if file_exists:
                download_asc_on_az(account_url)
                # process until download_dir is empty
                process_files()
                # copy ready files to s3 ready bucket
                logger.info('Uploading files')
                copy_files_on_az(LOCAL_READY_DIR, account_url, DECRYPTED_DONE_LOCATION, prefix)
                # TODO Finish method below
                archive_on_az(bucket, key)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            message = 'Unexpected error while processing upload s3://{bucket}/{key}, with message \"{message}\". The file ' \
                      'has been moved to the error folder. ' \
                      'Stack trace follows: {trace}'.format(message=exc_value, bucket=bucket, key=key,
                                                            trace=''.join('!! '
                                                                          + line for line in lines))
            logger.error(message)
            error_on_az(bucket, key)
            return 'failure.'
    return 'success.'
