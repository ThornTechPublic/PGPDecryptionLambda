import base64
import json
import unittest
from importlib.resources import files
from unittest import mock

import azure.functions
from aws_lambda_context import LambdaContext as awscontext

import src.main.AWS.aws_handler as aws_handler
import src.main.Azure.PgpDecrypt.azure_handler as azure_handler
import src.main.GCP.google_handler as google_handler
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
        aws_handler.invoke(json.loads(s3event), awscontext)
        download_file_on_s3.assert_called_with('chris-sftpgw-pgp-encrypted', 'test.txt.gpg')
        remove.assert_called_with('resource/test_file.txt.gpg')
        copy_file_on_s3.assert_called_with('/tmp/downloads/test_file.txt', None, 'test.txt')

    @mock.patch('src.main.GCP.google_handler.os.remove')
    @mock.patch.multiple('src.main.GCP.google_handler',
                         download_file_on_gcp=mock.DEFAULT,
                         download_asc_on_gcp=mock.DEFAULT,
                         copy_file_on_gcp=mock.DEFAULT,
                         get_client=mock.DEFAULT)
    def test_gcp_event(self, remove, download_file_on_gcp, download_asc_on_gcp, copy_file_on_gcp, get_client):
        download_file_on_gcp.return_value = 'resource/test_file.txt.gpg'
        gcpevent = files('event').joinpath('gcpevent.json').read_text()
        gcpcontext = "{event_id: 5151942645931035, timestamp: 2022-07-21T19:23:54.581Z, event_type: google.storage.object.finalize, resource: {'service': 'storage.googleapis.com', 'name': 'projects/_/buckets/chris-pgp-encrypted-dev/objects/test_file.txt.gpg', 'type': 'storage#object'}}"
        google_handler.invoke(json.loads(gcpevent), gcpcontext)
        download_file_on_gcp.assert_called_with('chris-pgp-encrypted-dev', 'test_file.txt.gpg')
        remove.assert_called_with('resource/test_file.txt.gpg')
        copy_file_on_gcp.assert_called_with('/tmp/downloads/test_file.txt', None, 'test_file.txt')

    @mock.patch('src.main.Azure.PgpDecrypt.azure_handler.os.remove')
    @mock.patch.multiple('src.main.Azure.PgpDecrypt.azure_handler',
                         download_file_on_az=mock.DEFAULT,
                         download_asc_on_az=mock.DEFAULT,
                         copy_file_on_az=mock.DEFAULT)
    def test_azure_event(self, remove, download_file_on_az, download_asc_on_az, copy_file_on_az):
        download_file_on_az.return_value = 'resource/test_file.txt.gpg'

        event_data = json.loads(files('event').joinpath('azureevent.json').read_bytes())
        event_data["data"] = base64.b64decode(event_data["data"].encode("UTF-8"))
        azureevent = azure.functions.blob.InputStream(**event_data)

        azure_handler.invoke(azureevent)
        download_file_on_az.assert_called_with('pgptest1', 'test_file.txt.gpg')
        remove.assert_any_call('resource/test_file.txt.gpg')
        copy_file_on_az.assert_called_with('/tmp/downloads/test_file.txt', None, 'test_file.txt')


if __name__ == '__main__':
    unittest.main()
