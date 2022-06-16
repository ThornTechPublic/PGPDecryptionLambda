from res.sharedconstants import *
import os
import re
import zipfile
from os.path import join


def decrypt(source_filepath):
    logger.info(os.stat(source_filepath))
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
    with zipfile.ZipFile(source_filename) as zf:
        zf.extractall(dest_dir)


def process_files():
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
                    try:
                        os.remove(file_path)
                    except FileNotFoundError:
                        logger.info(f"{file_path} already deleted")
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
