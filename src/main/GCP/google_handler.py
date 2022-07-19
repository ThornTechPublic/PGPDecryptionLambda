from src.main.res.sharedconstants import *
from src.main.res.pgpDecrypt import process_file, import_gpg_key

import os
import sys
import traceback
from os.path import join
from urllib import parse
import re

from google.cloud.storage import Bucket, Client
client = Client()


def move_on_gcp(dest_pattern: str, bucket_name: str, remote_filepath: str):
    bucket_obj = Bucket(client, bucket_name)
    source_blob = bucket_obj.blob(remote_filepath)
    path, filename = os.path.split(remote_filepath)
    dest_remote_filepath = dest_pattern.replace(r"\1", path).replace(r"\2", filename).strip('/')
    logger.info('move original file to ' + dest_remote_filepath)
    bucket_obj.copy_blob(source_blob, bucket_obj, dest_remote_filepath, client)
    logger.info('deleting original upload file')
    source_blob.delete(client)


def download_file_on_gcp(bucket_name: str, remote_filepath: str):
    download_filepath = join(DOWNLOAD_DIR, trim_path_to_filename(randomize_filename(remote_filepath)))
    logger.info(f'downloading gcp://{bucket_name}/{remote_filepath} to {download_filepath}')
    Bucket(client, bucket_name).blob(remote_filepath).download_to_filename(download_filepath, client)
    return download_filepath


# download the private encryption key from gcp
def download_asc_on_gcp():
    logger.info(f'Attempting to download key from gcp://{PGP_KEY_LOCATION}/{ASC_REMOTE_KEY}')
    blob_obj = Bucket(client, PGP_KEY_LOCATION).blob(ASC_REMOTE_KEY)
    import_gpg_key(blob_obj.download_as_bytes(client).decode('UTF-8'))


def copy_file_on_gcp(local_filepath: str, bucket_name: str, remote_filepath: str):
    logger.info(f'Uploading: {local_filepath} to {bucket_name}/{remote_filepath}')
    Bucket(client, bucket_name).blob(remote_filepath).upload_from_filename(local_filepath)


# Filepath here is the full path including folders and the filename (and extension) of the remote file
# Store file in error directory
def error_on_gcp(bucket: str, filepath: str):
    if ERROR:
        move_on_gcp(ERROR, bucket, filepath)


# Archive and delete the file
def archive_on_gcp(bucket: str, filepath: str):
    if ARCHIVE:
        move_on_gcp(ARCHIVE, bucket, filepath)


def invoke(event, context):
    logger.info('Google Event: ' + str(event))
    bucket_name = event["bucket"]
    remote_filepath = parse.unquote_plus(event["name"])

    if not remote_filepath.endswith(('.pgp', '.gpg', '.zip')):
        logger.info(f'File {remote_filepath} is not an encrypted file... Skipping')
    elif ARCHIVE and re.fullmatch(ARCHIVE.replace(r"\1/", ".*/?", 1).replace(r"\1", ".+").replace(r"\2", "[^/]+"), remote_filepath) is not None:
        logger.info('Archive event triggered... Skipping')
    elif ERROR and re.fullmatch(ERROR.replace(r"\1/", ".*/?", 1).replace(r"\1", ".+").replace(r"\2", "[^/]+"), remote_filepath) is not None:
        logger.info('Error event triggered... Skipping')
    else:
        try:
            logger.info(f'Begin Processing gcp://{bucket_name}/{remote_filepath}')

            if '.' not in remote_filepath:
                logger.info(f'Skipping processing of folder {remote_filepath}')
                return
            elif int(event['size']) == 0:
                logger.info(f'File {remote_filepath} is a placeholder file... Skipping')
                return

            local_filepath = download_file_on_gcp(bucket_name, remote_filepath)
            download_asc_on_gcp()
            local_filepath = process_file(local_filepath)
            # copy ready files to gcp ready bucket
            logger.info('Uploading file')
            dest_remote_filepath = os.path.splitext(remote_filepath)[0]
            copy_file_on_gcp(local_filepath, DECRYPTED_DONE_LOCATION, dest_remote_filepath)
            archive_on_gcp(bucket_name, remote_filepath)
        except Exception as ex:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            message = f'Unexpected error while processing upload gcp://{bucket_name}/{remote_filepath}, with message "{exc_value}". \
                      The file has been moved to the error folder. Stack trace follows: {"".join("!! " + line for line in lines)}'
            logger.error(message)
            error_on_gcp(bucket_name, remote_filepath)
            raise ex
