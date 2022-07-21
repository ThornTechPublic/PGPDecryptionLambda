from .sharedconstants import *
import os
import re
import zipfile
from os.path import join


def import_gpg_key(import_key: str):
    import_result = gpg.import_keys(import_key)
    logger.info(f'key import result fingerprint: {", ".join(import_result.fingerprints)}')

def decrypt(source_filepath: str):
    logger.info(os.stat(source_filepath))
    with open(source_filepath, 'rb') as f:
        source_filename = trim_path_to_filename(source_filepath)
        decrypt_path = join(DECRYPT_DIR, re.sub(r'\.(pgp|gpg)$', '', source_filename))
        logger.info('Decrypting to {}'.format(decrypt_path))
        data = gpg.decrypt_file(f, always_trust=True, output=decrypt_path, passphrase=PASSPHRASE)
        logger.info('Decrypt status: {}'.format(data.status))
        return decrypt_result(decrypt_path, data.ok)


def sort_local_file(local_filepath: str, processed_dir: str):
    logger.info(f'local sorting: {local_filepath}')
    destination = join(processed_dir, trim_path_to_filename(local_filepath))
    if local_filepath.endswith('.zip') or local_filepath.endswith('.pgp') or local_filepath.endswith('.gpg'):
        destination = join(DOWNLOAD_DIR, trim_path_to_filename(local_filepath))
    logger.info(f'local sorting {local_filepath} to {destination}')
    os.rename(local_filepath, destination)
    return destination


# sorts files to ready if done unzipping/decrypting or back to downloads if more work is needed
def sort_local_files(filepaths: list, processed_dir: str):
    return [sort_local_file(filepath, processed_dir) for filepath in filepaths]


def unzip(source_filename: str, dest_dir: str):
    with zipfile.ZipFile(source_filename) as zf:
        zf.extractall(dest_dir)


def process_files():
    raise NotImplementedError("Not to be used for the time being")
    dir_contents = os.listdir(DOWNLOAD_DIR)
    while dir_contents:
        for f in dir_contents:
            local_filepath = join(DOWNLOAD_DIR, f)
            if f.endswith(('.pgp', '.gpg')):
                logger.info('Decrypting {}'.format(local_filepath))
                decrypted = decrypt(local_filepath)
                if not decrypted.ok:
                    raise EnvironmentError('Decryption failed. Do you have the right key?')
                else:
                    try:
                        os.remove(local_filepath)
                    except FileNotFoundError:
                        logger.info(f"{local_filepath} already deleted")
                    sort_local_files(trim_path_to_directory(decrypted.path), DOWNLOAD_DIR)
            elif f.endswith('.zip'):
                # process zip file
                logger.info('Unzipping {}'.format(local_filepath))
                unzip(local_filepath, LOCAL_UNZIPPED_DIR)
                os.remove(local_filepath)
                sort_local_files(LOCAL_UNZIPPED_DIR, DOWNLOAD_DIR)
            else:
                sort_local_files(DOWNLOAD_DIR, LOCAL_READY_DIR)
        dir_contents = os.listdir(DOWNLOAD_DIR)


def process_file(local_filepath: str):
    if local_filepath.endswith(('.pgp', '.gpg')):
        logger.info(f'Decrypting {local_filepath}')
        decrypted = decrypt(local_filepath)
        if not decrypted.ok:
            raise EnvironmentError('Decryption failed. Do you have the right key?')
        else:
            try:
                os.remove(local_filepath)
            except FileNotFoundError:
                logger.info(f"{local_filepath} already deleted")
            return sort_local_file(decrypted.path, DOWNLOAD_DIR)
    # elif local_filepath.endswith('.zip'):
    #     # process zip file
    #     logger.info(f'Unzipping {local_filepath}')
    #     unzip(local_filepath, LOCAL_UNZIPPED_DIR)
    #     os.remove(local_filepath)
    #     sort_local_files(LOCAL_UNZIPPED_DIR, DOWNLOAD_DIR)
    # else:
    #     sort_local_files(DOWNLOAD_DIR, LOCAL_READY_DIR)