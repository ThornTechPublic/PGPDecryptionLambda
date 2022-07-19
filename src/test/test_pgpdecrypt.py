import unittest
from importlib.resources import files

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


if __name__ == '__main__':
    unittest.main()
