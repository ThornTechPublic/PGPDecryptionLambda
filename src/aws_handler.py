from sharedconstants import *
from pgplambda import process_files

import logging
import os
import sys
import traceback
from os.path import join, isfile
from urllib import parse

import boto3
from botocore.exceptions import ClientError
S3 = boto3.resource('s3')


def move_on_s3(dest_folder: str, bucket: str, key: str):
    download_filename = trim_path_to_filename(key)
    new_key = join(dest_folder, download_filename)
    logger.info('move original file to ' + new_key)
    S3.Object(bucket, new_key).copy_from(CopySource='{0}/{1}'.format(bucket, key))
    logger.info('deleting original upload file')
    S3.Object(bucket, key).delete()


def download_file_on_s3(bucket: str, download_path: str, key: str):
    logger.info('downloading s3://{0}/{1} to {2}'.format(bucket, key, download_path))
    try:
        S3.Object(bucket, key).download_file(download_path)
        exists = True
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            exists = False
            logger.warning(
                'attempt to download s3://{0}/{1} failed, it was not found. Most likely file was already processed.'.format(
                    bucket, key))
        else:
            raise e
    return exists


# download the private encryption key from s3
def download_asc_on_s3():
    if not os.path.exists(ASC_LOCAL_PATH):
        os.mkdir(ASC_LOCAL_PATH)
    logger.info('Attempting to download key from s3://{}/{}'.format(PGP_KEY_LOCATION, ASC_REMOTE_KEY))
    local_key = join(ASC_LOCAL_PATH, ASC_REMOTE_KEY)
    S3.Object(PGP_KEY_LOCATION, ASC_REMOTE_KEY).download_file(local_key)
    # Disable logging of key data while importing the key
    with open(local_key, "r") as f:
        key_data = f.read()
        import_result = gpg.import_keys(key_data)
    logger.info('key import result fingerprint: {}'.format(', '.join(import_result.fingerprints)))


def copy_files_on_s3(copy_source_dir: str, bucket: str, prefix: str):
    for f in os.listdir(copy_source_dir):
        file_path = join(copy_source_dir, f)
        if isfile(file_path):
            upload_path = join(prefix, f)
            logger.info('Uploading: {} to {}'.format(file_path, upload_path))
            S3.Object(bucket, upload_path).upload_file(file_path)


# Filepath here is the full path including folders and the filename (and extension) of the remote file
# Store file in error directory
def error_on_s3(bucket: str, filepath: str):
    if ERROR:
        move_on_s3('error/', bucket, filepath)


# Archive and delete the file
def archive_on_s3(bucket: str, filepath: str):
    if ARCHIVE:
        move_on_s3('archive/', bucket, filepath)


def invoke(event, context):
    print(event)
    logger.debug('S3 Event: ' + str(event))
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = parse.unquote_plus(record['s3']['object']['key'])
        prefix = trim_path_to_directory(key)
        download_filename = trim_path_to_filename(key)

        if not key.endswith(('.pgp', '.gpg')):
            logger.info(f'File {key} is not an encrypted file... Skipping')
            continue

        if ARCHIVE and prefix.startswith('archive'):
            logger.debug('Archive event triggered... Skipping')
            continue
        elif ERROR and prefix.startswith('error'):
            logger.debug('Error event triggered... Skipping')
            continue

        try:
            reset_folder(DOWNLOAD_DIR)
            reset_folder(DECRYPT_DIR)
            reset_folder(LOCAL_UNZIPPED_DIR)
            reset_folder(LOCAL_READY_DIR)

            logger.info('Begin Processing s3://{0}/{1}'.format(bucket, key))

            if not download_filename:
                logger.info('Skipping processing of folder {0}'.format(key))
                continue
            elif int(record['s3']['object']['size']) == 0:
                logger.info('File {key} is a placeholder file... Skipping'.format(key=key))
                continue

            download_path = join(DOWNLOAD_DIR, download_filename)

            file_exists = download_file_on_s3(bucket, download_path, key)

            if file_exists:
                download_asc_on_s3()
                # process until download_dir is empty
                process_files()
                # copy ready files to s3 ready bucket
                logger.info('Uploading files')
                copy_files_on_s3(LOCAL_READY_DIR, DECRYPTED_DONE_LOCATION, prefix)
                archive_on_s3(bucket, key)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            message = 'Unexpected error while processing upload s3://{bucket}/{key}, with message \"{message}\". The file ' \
                      'has been moved to the error folder. ' \
                      'Stack trace follows: {trace}'.format(message=exc_value, bucket=bucket, key=key,
                                                            trace=''.join('!! '
                                                                          + line for line in lines))
            logger.error(message)
            error_on_s3(bucket, key)
            return 'failure.'
    return 'success.'
