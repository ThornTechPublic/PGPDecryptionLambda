import json
import unittest
from importlib.resources import files
from unittest import mock

from aws_lambda_context import LambdaContext as context

import src.main.AWS.aws_handler as aws_handler
import src.main.res.pgpDecrypt as pgpDecrypt
import src.main.res.sharedconstants as sharedconstants


class TestPgpDecrypt(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        pgpDecrypt.import_gpg_key(
            files('resource.keys').joinpath('pgptestPrivate.asc').read_text()
        )

    def test_key_was_imported(self):
        keys = sharedconstants.gpg.list_keys()
        uids = [uid for key in keys for uid in key.get('uids')]
        self.assertIn("pgptest <pgptest@email.com>", uids)

    def test_decrypt(self):
        result = pgpDecrypt.decrypt('resource/test_file.txt.gpg')
        self.assertEqual(result.ok, True)

    @mock.patch('src.main.AWS.aws_handler.os.remove')
    @mock.patch.multiple('src.main.AWS.aws_handler',
                         download_file_on_s3=mock.DEFAULT,
                         download_asc_on_s3=mock.DEFAULT,
                         copy_file_on_s3=mock.DEFAULT)
    def test_s3_event(self, remove, download_file_on_s3, download_asc_on_s3, copy_file_on_s3):
        download_file_on_s3.return_value = 'resource/test_file.txt.gpg'
        s3event = files('event').joinpath('s3event.json').read_text()
        aws_handler.invoke(json.loads(s3event), context)
        download_file_on_s3.assert_called_with('chris-sftpgw-pgp-encrypted', 'test.txt.gpg')
        remove.assert_called_with('resource/test_file.txt.gpg')
        copy_file_on_s3.assert_called_with('/tmp/downloads/test_file.txt', None, 'test.txt')


if __name__ == '__main__':
    unittest.main()
