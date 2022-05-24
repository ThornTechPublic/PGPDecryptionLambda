import collections
import logging
import os
import re
import shutil
import sys
import traceback
import zipfile
from os import listdir, mkdir
from os.path import join, isfile
from urllib import parse

import boto3
import gnupg
from botocore.exceptions import ClientError

# Logger
logger = logging.getLogger()
logger.setLevel(logging.getLevelName(os.environ.get('LOG_LEVEL', default='INFO')))
logger.info('Loading function')

# AWS resources
s3 = boto3.resource('s3')

# Global variables
actions_taken = []
asc_key_downloaded_for_client = ''
PGP_KEY_S3_BUCKET = os.environ.get('PGP_KEY_LOCATION')
ASC_REMOTE_KEY = os.environ.get('PGP_KEY_NAME')
DECRYPTED_DONE_BUCKET = os.environ.get('DECRYPTED_DONE_BUCKET')

# Directories
download_dir = '/tmp/downloads/'
decrypt_dir = '/tmp/decrypted/'
local_unzipped_dir = '/tmp/unzipped/'
local_ready_dir = '/tmp/ready/'
asc_local_path = '/tmp/asc/'
ready_dir = 'ready/'

# GPG
gnupg_home = '/tmp/gnupg'
gpg = gnupg.GPG(gnupghome=gnupg_home)
decrypt_result = collections.namedtuple('DecryptResult', ['path', 'ok'])


# deletes the contents of a local folder and recreates it
def reset_folder(local_path):
    logger.debug('deleting local contents of {}'.format(local_path))
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    mkdir(local_path)


def trim_path_to_filename(path):
    if path.rfind('/') != -1:
        path = path[path.rfind('/') + 1:len(path)]
    return path


def trim_path_to_directory(path):
    if path.rfind('/') != -1:
        path = path[0:path.rfind('/') + 1]
    return path


# Store file in error directory on s3
def error_on_s3(bucket, key):
    move_on_s3('error/', bucket, key)


def move_on_s3(dest_folder, bucket, key):
    download_filename = trim_path_to_filename(key)
    new_key = join(dest_folder, download_filename)
    logger.info('move original file to ' + new_key)
    s3.Object(bucket, new_key).copy_from(CopySource='{0}/{1}'.format(bucket, key))
    logger.info('deleting original upload file')
    s3.Object(bucket, key).delete()


def download_file(bucket, download_path, key):
    logger.info('downloading s3://{0}/{1} to {2}'.format(bucket, key, download_path))
    try:
        s3.meta.client.download_file(bucket, key, download_path)
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
def download_asc():
    asc_dir = trim_path_to_directory(asc_local_path)
    if not os.path.exists(asc_dir):
        mkdir(asc_dir)
    logger.info('Attempting to download key from s3://{}/{}'.format(PGP_KEY_S3_BUCKET, ASC_REMOTE_KEY))
    local_key = join(asc_local_path, ASC_REMOTE_KEY)
    s3.meta.client.download_file(PGP_KEY_S3_BUCKET, ASC_REMOTE_KEY, local_key)
    key_data = open(local_key).read()
    # Disable logging of key data while importing the key
    level = logger.level
    logger.setLevel(logging.WARN)
    import_result = gpg.import_keys(key_data)
    logger.setLevel(level)
    logger.info('key import result fingerprint: {}'.format(', '.join(import_result.fingerprints)))


def decrypt(source_filepath):
    actions_taken.append('DECRYPTED')
    with open(source_filepath, 'rb') as f:
        source_filename = trim_path_to_filename(source_filepath)
        decrypt_path = join(decrypt_dir, re.sub(r'\.(pgp|gpg)$', '', source_filename))
        logger.info('Decrypting to {}'.format(decrypt_path))
        data = gpg.decrypt_file(f, always_trust=True, output=decrypt_path)
        logger.info('Decrypt status: {}'.format(data.status))
        return decrypt_result(decrypt_path, data.ok)


def sort_local_file(file_path, processed_dir):
    logger.info(f'local sorting: {file_path}')
    destination = join(processed_dir, trim_path_to_filename(file_path))
    if file_path.endswith('.zip') or file_path.endswith('.pgp') or file_path.endswith('.gpg'):
        destination = join(download_dir, trim_path_to_filename(file_path))
    logger.info(f'local sorting {file_path} to {destination}')
    os.rename(file_path, destination)


# sorts files to ready if done unzipping/decrypting or back to downloads if more work is needed
def sort_local_files(source_dir, processed_dir):
    for f in listdir(source_dir):
        sort_local_file(join(source_dir, f), processed_dir)


def unzip(source_filename, dest_dir):
    actions_taken.append('UNZIPPED')
    with zipfile.ZipFile(source_filename) as zf:
        zf.extractall(dest_dir)


def process_files():
    while listdir(download_dir):
        for f in listdir(download_dir):
            file_path = join(download_dir, f)
            if f.endswith('.pgp') or f.endswith('.gpg'):
                download_asc()
                logger.info('Decrypting {}'.format(file_path))
                decrypted = decrypt(file_path)
                if not decrypted.ok:
                    raise EnvironmentError('Decryption failed. Do you have the right key?')
                else:
                    os.remove(file_path)
                    sort_local_files(trim_path_to_directory(decrypted.path), download_dir)

            elif f.endswith('.zip'):
                # process zip file
                logger.info('Unzipping {}'.format(file_path))
                unzip(file_path, local_unzipped_dir)
                os.remove(file_path)
                sort_local_files(local_unzipped_dir, download_dir)
            else:
                sort_local_files(download_dir, local_ready_dir)


def copy_files(copy_source_dir, bucket):
    for f in listdir(copy_source_dir):
        file_path = join(copy_source_dir, f)
        if isfile(file_path):
            logger.info('Processing: ' + file_path)
            logger.info('Uploading: {} to {}'.format(file_path, f))
            s3.meta.client.upload_file(file_path, bucket, f)


# Archive and delete the file in the s3 bucket
def archive_on_s3(bucket, key):
    move_on_s3('archive/', bucket, key)


def move_on_s3(dest_folder, bucket, key):
    # store file in error
    download_filename = trim_path_to_filename(key)
    new_key = join(dest_folder, download_filename)
    logger.info('move original file to ' + new_key)
    s3.Object(bucket, new_key).copy_from(CopySource='{}/{}'.format(bucket, key))
    logger.info('deleting original upload file')
    s3.Object(bucket, key).delete()


def lambda_handler(event, context):
    logger.debug('S3 Event: ' + str(event))
    for record in event['Records']:
        del actions_taken[:]
        bucket = record['s3']['bucket']['name']
        key = parse.unquote_plus(record['s3']['object']['key'])
        prefix = trim_path_to_directory(key)
        download_filename = trim_path_to_filename(key)

        if prefix == 'archive/':
            logger.debug('Archive event triggered... Skipping')
            continue
        elif prefix == 'error/':
            logger.debug('Error event triggered... Skipping')
            continue

        try:
            reset_folder(download_dir)
            reset_folder(decrypt_dir)
            reset_folder(local_unzipped_dir)
            reset_folder(local_ready_dir)

            logger.info('Begin Processing s3://{0}/{1}'.format(bucket, key))

            if not download_filename:
                logger.info('Skipping processing of folder {0}'.format(key))
                continue

            download_path = join(download_dir, download_filename)

            file_exists = download_file(bucket, download_path, key)

            if file_exists:
                # process until download_dir is empty
                process_files()

                # copy ready files to s3 ready bucket
                logger.info('Uploading files')
                copy_files(local_ready_dir, DECRYPTED_DONE_BUCKET)
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
