import base64

import functions_framework

from res.sharedconstants import *
from res.pgpDecrypt import process_file, import_gpg_key

import os
import sys
import json
import traceback
from os.path import join
from urllib import parse
import re

from google.cloud.storage import Bucket, Client
import google.cloud.logging as google_logger

client = google_logger.Client()
client.setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))

def get_client():
    return Client()


def move_on_gcp(dest_pattern: str, bucket_name: str, remote_filepath: str):
    bucket_obj = Bucket(get_client(), bucket_name)
    source_blob = bucket_obj.blob(remote_filepath)
    path, filename = os.path.split(remote_filepath)
    dest_remote_filepath = dest_pattern.replace(r"\1", path).replace(r"\2", filename).strip('/')
    logger.info('move original file to ' + dest_remote_filepath)
    bucket_obj.copy_blob(source_blob, bucket_obj, dest_remote_filepath, get_client())
    logger.info('deleting original upload file')
    source_blob.delete(get_client())


def download_file_on_gcp(bucket_name: str, remote_filepath: str):
    download_filepath = join(DOWNLOAD_DIR, trim_path_to_filename(randomize_filename(remote_filepath)))
    logger.info(f'downloading gcp://{bucket_name}/{remote_filepath} to {download_filepath}')
    Bucket(get_client(), bucket_name).blob(remote_filepath).download_to_filename(download_filepath, get_client())
    return download_filepath


# download the private encryption key from gcp
def download_asc_on_gcp():
    logger.info(f'Attempting to download key from gcp://{PGP_KEY_LOCATION}/{ASC_REMOTE_KEY}')
    blob_obj = Bucket(get_client(), PGP_KEY_LOCATION).blob(ASC_REMOTE_KEY)
    import_gpg_key(blob_obj.download_as_bytes(get_client()).decode('UTF-8'))


def copy_file_on_gcp(local_filepath: str, bucket_name: str, remote_filepath: str):
    logger.info(f'Uploading: {local_filepath} to {bucket_name}/{remote_filepath}')
    Bucket(get_client(), bucket_name).blob(remote_filepath).upload_from_filename(local_filepath)


# Filepath here is the full path including folders and the filename (and extension) of the remote file
# Store file in error directory
def error_on_gcp(bucket: str, filepath: str):
    if ERROR:
        move_on_gcp(ERROR, bucket, filepath)


# Archive and delete the file
def archive_on_gcp(bucket: str, filepath: str):
    if ARCHIVE:
        move_on_gcp(ARCHIVE, bucket, filepath)


@functions_framework.http
def invoke(event):
    event_data = json.loads(base64.b64decode(json.loads(event.data).get('message').get('data')))
    logger.debug('Google Event: ' + str(event_data))

    bucket_name = event_data["bucket"]
    remote_filepath = parse.unquote_plus(event_data["name"])

    if not remote_filepath.endswith(('.pgp', '.gpg', '.zip')):
        logger.info(f'File {remote_filepath} is not an encrypted file... Skipping')
        return 'OK'
    elif ARCHIVE and re.fullmatch(ARCHIVE.replace(r"\1/", ".*/?", 1).replace(r"\1", ".+").replace(r"\2", "[^/]+"), remote_filepath) is not None:
        logger.info('Archive event triggered... Skipping')
        return 'OK'
    elif ERROR and re.fullmatch(ERROR.replace(r"\1/", ".*/?", 1).replace(r"\1", ".+").replace(r"\2", "[^/]+"), remote_filepath) is not None:
        logger.info('Error event triggered... Skipping')
        return 'OK'
    else:
        try:
            logger.info(f'Begin Processing gcp://{bucket_name}/{remote_filepath}')

            if '.' not in remote_filepath:
                logger.info(f'Skipping processing of folder {remote_filepath}')
                return
            elif int(event_data['size']) == 0:
                logger.info(f'File {remote_filepath} is a placeholder file... Skipping')
                return 'OK'

            local_filepath = download_file_on_gcp(bucket_name, remote_filepath)
            download_asc_on_gcp()
            local_filepath = process_file(local_filepath)
            # copy ready files to gcp ready bucket
            logger.info('Uploading file')
            dest_remote_filepath = os.path.splitext(remote_filepath)[0]
            copy_file_on_gcp(local_filepath, DECRYPTED_DONE_LOCATION, dest_remote_filepath)
            archive_on_gcp(bucket_name, remote_filepath)
            return 'OK'
        except Exception as ex:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            message = f'Unexpected error while processing upload gcp://{bucket_name}/{remote_filepath}, with message "{exc_value}". \
                      The file has been moved to the error folder. Stack trace follows: {"".join("!! " + line for line in lines)}'
            logger.error(message)
            error_on_gcp(bucket_name, remote_filepath)
            return 'FAILURE'
