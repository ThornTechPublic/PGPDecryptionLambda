import logging
import shutil
import os
import collections
import gnupg
import random
from datetime import datetime

# Logger
logger = logging.getLogger()
logger.setLevel(logging.getLevelName(os.getenv('LOG_LEVEL', default='INFO')))
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


def timestamp_filename(filepath: str):
    stamp = datetime.utcnow().isoformat(timespec="seconds").replace(":", "_")
    path, filename = os.path.split(filepath)
    return os.path.join(path, (stamp+'.').join(filename.split('.', 1)))


# Global variables
PGP_KEY_LOCATION = os.getenv('PGP_KEY_LOCATION')
ASC_REMOTE_KEY = os.getenv('PGP_KEY_NAME')
DECRYPTED_DONE_LOCATION = os.getenv('DECRYPTED_DONE_LOCATION')
PASSPHRASE = os.getenv("PGP_PASSPHRASE", None)
if PASSPHRASE == "":
    PASSPHRASE = None
CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", None)

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
create_folder_if_not_exists(DOWNLOAD_DIR)
create_folder_if_not_exists(DECRYPT_DIR)
create_folder_if_not_exists(LOCAL_UNZIPPED_DIR)
create_folder_if_not_exists(LOCAL_READY_DIR)

# Feature Flags
ARCHIVE = os.getenv('ARCHIVE', default=False)
if isinstance(ARCHIVE, str):
    ARCHIVE = ARCHIVE.upper().strip() != "FALSE"
ERROR = os.getenv('ERROR', default=False)
if isinstance(ERROR, str):
    ERROR = ERROR.upper().strip() != "FALSE"

trim_path_to_filename = os.path.basename
trim_path_to_directory = os.path.dirname
