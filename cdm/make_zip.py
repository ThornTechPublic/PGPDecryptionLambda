import zipfile

with zipfile.ZipFile("pgpGoogleArchive.zip", "w") as zf:
    zf.write("main.py")
    zf.write("../src/requirements.txt", "requirements.txt")
    zf.write("../src/google_handler.py", "google_handler.py")
    zf.write("../src/res/pgpDecrypt.py", "src/res/pgpDecrypt.py")
    zf.write("../src/res/sharedconstants.py", "src/res/sharedconstants.py")
