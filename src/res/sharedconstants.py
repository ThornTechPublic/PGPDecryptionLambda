import logging
import shutil
import os
import collections
import gnupg
import random

# Logger
logger = logging.getLogger()
logger.setLevel(logging.getLevelName(os.environ.get('LOG_LEVEL', default='INFO')))
logger.info('Loading function')


# deletes the contents of a local folder and recreates it
def create_folder_if_not_exists(local_path: str):
    if not os.path.exists(local_path):
        os.mkdir(local_path)


def reset_folder(local_path: str):
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    os.mkdir(local_path)


def randomize_filename(filepath: str):
    num = random.randint(10000000, 100000000)
    return str(num).join(os.path.splitext(filepath))


# Global variables
PGP_KEY_LOCATION = os.environ.get('PGP_KEY_LOCATION')
ASC_REMOTE_KEY = os.environ.get('PGP_KEY_NAME')
DECRYPTED_DONE_LOCATION = os.environ.get('DECRYPTED_DONE_LOCATION')
PASSPHRASE = os.environ.get("PGP_PASSPHRASE", None)
if PASSPHRASE == "":
    PASSPHRASE = None
CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

# Directories
DOWNLOAD_DIR = '/tmp/downloads/'
DECRYPT_DIR = '/tmp/decrypted/'
LOCAL_UNZIPPED_DIR = '/tmp/unzipped/'
LOCAL_READY_DIR = '/tmp/ready/'
ASC_LOCAL_PATH = '/tmp/asc/'
GNUPG_HOME = '/tmp/gnupg'
reset_folder(GNUPG_HOME)
gpg = gnupg.GPG(gnupghome=GNUPG_HOME, gpgbinary="/usr/bin/gpg")
decrypt_result = collections.namedtuple('DecryptResult', ['path', 'ok'])

# Feature Flags
ARCHIVE = os.environ.get('ARCHIVE', default=False)
ERROR = os.environ.get('ERROR', default=False)

trim_path_to_filename = os.path.basename
trim_path_to_directory = os.path.dirname
