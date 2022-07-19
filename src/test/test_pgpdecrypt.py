import unittest
import src.main.res.pgpDecrypt as pgpDecrypt
import os

class TestPgpDecrypt(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.chdir(os.path.split(__file__)[0])
        with open('resource/keys/pgptestPrivate.asc', 'r') as key:
            pgpDecrypt.import_gpg_key(key.read())


    def test_decrypt(self):
        result = pgpDecrypt.decrypt('resource/test_file.txt.gpg')
        self.assertEqual(result.ok, True)


if __name__ == '__main__':
    unittest.main()
