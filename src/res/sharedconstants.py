import logging
import shutil
import os
import collections
import gnupg

# Logger
logger = logging.getLogger()
logger.setLevel(logging.getLevelName(os.environ.get('LOG_LEVEL', default='INFO')))
logger.info('Loading function')

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
gpg = gnupg.GPG(gnupghome=GNUPG_HOME)
decrypt_result = collections.namedtuple('DecryptResult', ['path', 'ok'])

# Feature Flags
ARCHIVE = os.environ.get('ARCHIVE', default=False)
ERROR = os.environ.get('ERROR', default=False)

trim_path_to_filename = os.path.basename
trim_path_to_directory = os.path.dirname


# deletes the contents of a local folder and recreates it
def reset_folder(local_path):
    logger.debug('deleting local contents of {}'.format(local_path))
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    os.mkdir(local_path)
