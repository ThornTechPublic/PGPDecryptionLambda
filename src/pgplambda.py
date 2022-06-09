import collections
import logging
import os
import re
import shutil
import sys
import traceback
import zipfile
from os.path import join, isfile
from urllib import parse

import boto3
import gnupg
from botocore.exceptions import ClientError

## TODO remove s3 and aws from strings in general funcs, use gen funcs in other gen funcs, define az and gcp funcs

# Logger
logger = logging.getLogger()
logger.setLevel(logging.getLevelName(os.environ.get('LOG_LEVEL', default='INFO')))
logger.info('Loading function')

# AWS resources
S3 = boto3.resource('s3')

# Global variables
CLOUD_PROVIDER = os.environ.get("CLOUD_PROVIDER", default=None)
#actions_taken = []
#asc_key_downloaded_for_client = ''
PGP_KEY_LOCATION = os.environ.get('PGP_KEY_LOCATION')
ASC_REMOTE_KEY = os.environ.get('PGP_KEY_NAME')
DECRYPTED_DONE_BUCKET = os.environ.get('DECRYPTED_DONE_BUCKET')
PASSPHRASE = os.environ.get('PGP_PASSPHRASE')

# Directories
DOWNLOAD_DIR = '/tmp/downloads/'
DECRYPT_DIR = '/tmp/decrypted/'
LOCAL_UNZIPPED_DIR = '/tmp/unzipped/'
LOCAL_READY_DIR = '/tmp/ready/'
ASC_LOCAL_PATH = '/tmp/asc/'

# GPG
gnupg_home = '/tmp/gnupg'
gpg = gnupg.GPG(gnupghome=gnupg_home)
decrypt_result = collections.namedtuple('DecryptResult', ['path', 'ok'])

# Feature Flags
ARCHIVE = os.environ.get('ARCHIVE', default=False)
ERROR = os.environ.get('ERROR', default=False)


# deletes the contents of a local folder and recreates it
def reset_folder(local_path):
    logger.debug('deleting local contents of {}'.format(local_path))
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    os.mkdir(local_path)

def trim_path_to_filename(path):
    return os.path.basename(path)

def trim_path_to_directory(path):
    return os.path.dirname(path)

def move_on_s3(dest_folder, bucket, key):
    download_filename = trim_path_to_filename(key)
    new_key = join(dest_folder, download_filename)
    logger.info('move original file to ' + new_key)
    S3.Object(bucket, new_key).copy_from(CopySource='{0}/{1}'.format(bucket, key))
    logger.info('deleting original upload file')
    S3.Object(bucket, key).delete()

def download_file_on_s3(bucket, download_path, key):
    logger.info('downloading s3://{0}/{1} to {2}'.format(bucket, key, download_path))
    try:
        S3.meta.client.download_file(bucket, key, download_path)
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
    asc_dir = trim_path_to_directory(ASC_LOCAL_PATH)
    if not os.path.exists(asc_dir):
        os.mkdir(asc_dir)
    logger.info('Attempting to download key from s3://{}/{}'.format(PGP_KEY_LOCATION, ASC_REMOTE_KEY))
    local_key = join(ASC_LOCAL_PATH, ASC_REMOTE_KEY)
    S3.meta.client.download_file(PGP_KEY_LOCATION, ASC_REMOTE_KEY, local_key)
    # Disable logging of key data while importing the key
    level = logger.level
    logger.setLevel(logging.WARN)
    with open(local_key) as f:
        key_data = f.read()
        import_result = gpg.import_keys(key_data)
    logger.setLevel(level)
    logger.info('key import result fingerprint: {}'.format(', '.join(import_result.fingerprints)))

def copy_files_on_s3(copy_source_dir, bucket, prefix):
    for f in os.listdir(copy_source_dir):
        file_path = join(copy_source_dir, f)
        if isfile(file_path):
            upload_path = join(prefix, f)
            logger.info('Uploading: {} to {}'.format(file_path, upload_path))
            S3.meta.client.upload_file(file_path, bucket, upload_path)

def move_on_az(dest_folder, bucket, key):
    raise NotImplementedError("AZ funcs not implemented")

def download_file_on_az(bucket, download_path, key):
    raise NotImplementedError("AZ funcs not implemented")

def download_asc_on_az():
    raise NotImplementedError("AZ funcs not implemented")

def copy_files_on_az(copy_source_dir, bucket, prefix):
    raise NotImplementedError("AZ funcs not implemented")

def move_on_gcp(dest_folder, bucket, key):
    raise NotImplementedError("GCP funcs not implemented")

def download_file_on_gcp(bucket, download_path, key):
    raise NotImplementedError("GCP funcs not implemented")

def download_asc_on_gcp():
    raise NotImplementedError("GCP funcs not implemented")

def copy_files_on_gcp(copy_source_dir, bucket, prefix):
    raise NotImplementedError("GCP funcs not implemented")


def decrypt(source_filepath):
    #actions_taken.append('DECRYPTED')
    with open(source_filepath, 'rb') as f:
        source_filename = trim_path_to_filename(source_filepath)
        decrypt_path = join(DECRYPT_DIR, re.sub(r'\.(pgp|gpg)$', '', source_filename))
        logger.info('Decrypting to {}'.format(decrypt_path))
        data = gpg.decrypt_file(f, always_trust=True, output=decrypt_path, passphrase=PASSPHRASE)
        logger.info('Decrypt status: {}'.format(data.status))
        return decrypt_result(decrypt_path, data.ok)


def sort_local_file(file_path, processed_dir):
    logger.info(f'local sorting: {file_path}')
    destination = join(processed_dir, trim_path_to_filename(file_path))
    if file_path.endswith('.zip') or file_path.endswith('.pgp') or file_path.endswith('.gpg'):
        destination = join(DOWNLOAD_DIR, trim_path_to_filename(file_path))
    logger.info(f'local sorting {file_path} to {destination}')
    os.rename(file_path, destination)


# sorts files to ready if done unzipping/decrypting or back to downloads if more work is needed
def sort_local_files(source_dir, processed_dir):
    for f in os.listdir(source_dir):
        sort_local_file(join(source_dir, f), processed_dir)


def unzip(source_filename, dest_dir):
    #actions_taken.append('UNZIPPED')
    with zipfile.ZipFile(source_filename) as zf:
        zf.extractall(dest_dir)

if CLOUD_PROVIDER=="AWS":
    move_cloud = move_on_s3
    download_file_cloud = download_file_on_s3
    download_asc_cloud = download_asc_on_s3
    copy_files_cloud = copy_files_on_s3
elif CLOUD_PROVIDER=="AZ":
    move_cloud = move_on_az
    download_file_cloud = download_file_on_az
    download_asc_cloud = download_asc_on_az
    copy_files_cloud = copy_files_on_az
elif CLOUD_PROVIDER=="GCP":
    move_cloud = move_on_gcp
    download_file_cloud = download_file_on_gcp
    download_asc_cloud = download_asc_on_gcp
    copy_files_cloud = copy_files_on_gcp
else:
    raise RuntimeError("Not recognized cloud provider!")

# Filepath here is the full path including folders and the filename (and extension) of the remote file
# Store file in error directory
def error_cloud(bucket, filepath):
    if ERROR:
        move_cloud('error/', bucket, filepath)
# Archive and delete the file
def archive_cloud(bucket, filepath):
    if ARCHIVE:
        move_cloud('archive/', bucket, filepath)


def process_files():
    download_asc_cloud()
    dir_contents = os.listdir(DOWNLOAD_DIR)
    while dir_contents:
        for f in dir_contents:
            file_path = join(DOWNLOAD_DIR, f)
            if f.endswith(('.pgp', '.gpg')):
                logger.info('Decrypting {}'.format(file_path))
                decrypted = decrypt(file_path)
                if not decrypted.ok:
                    raise EnvironmentError('Decryption failed. Do you have the right key?')
                else:
                    os.remove(file_path)
                    sort_local_files(trim_path_to_directory(decrypted.path), DOWNLOAD_DIR)
            elif f.endswith('.zip'):
                # process zip file
                logger.info('Unzipping {}'.format(file_path))
                unzip(file_path, LOCAL_UNZIPPED_DIR)
                os.remove(file_path)
                sort_local_files(LOCAL_UNZIPPED_DIR, DOWNLOAD_DIR)
            else:
                sort_local_files(DOWNLOAD_DIR, LOCAL_READY_DIR)
        dir_contents = os.listdir(DOWNLOAD_DIR)

# TODO: Verify that the calls to cloud functions work for all cloud providers
# TODO: Remove s3 specific code and replace with general funcs
def lambda_handler(event, context):
    logger.debug('S3 Event: ' + str(event))
    for record in event['Records']:
        #del actions_taken[:]
        bucket = record['s3']['bucket']['name']
        key = parse.unquote_plus(record['s3']['object']['key'])
        prefix = trim_path_to_directory(key)
        download_filename = trim_path_to_filename(key)

        if not key.endswith(('.pgp', '.gpg')):
            logger.info('File {key} is not an encrypted file... Skipping'.format(key=key))
            continue

        if ARCHIVE and prefix == 'archive':
            logger.debug('Archive event triggered... Skipping')
            continue
        elif ERROR and prefix == 'error':
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

            file_exists = download_file_cloud(bucket, download_path, key)

            if file_exists:
                # process until download_dir is empty
                process_files()

                # copy ready files to s3 ready bucket
                logger.info('Uploading files')
                copy_files_cloud(LOCAL_READY_DIR, DECRYPTED_DONE_BUCKET, prefix)
                archive_cloud(bucket, key)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            message = 'Unexpected error while processing upload s3://{bucket}/{key}, with message \"{message}\". The file ' \
                      'has been moved to the error folder. ' \
                      'Stack trace follows: {trace}'.format(message=exc_value, bucket=bucket, key=key,
                                                            trace=''.join('!! '
                                                                          + line for line in lines))
            logger.error(message)
            error_cloud(bucket, key)
            return 'failure.'

    return 'success.'
