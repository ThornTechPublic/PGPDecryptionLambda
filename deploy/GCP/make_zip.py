if __name__ == "__main__":
    import zipfile
    import os

    os.chdir(os.path.split(__file__)[0])

    with zipfile.ZipFile("pgpGoogleArchive.zip", "w") as zf:
        zf.write("main.py")
        zf.write("../../src/main/GCP/requirements.txt", "requirements.txt")
        zf.write("../../src/main/GCP/google_handler.py", "google_handler.py")
        zf.write("../../src/main/res/pgpDecrypt.py", "src/main/res/pgpDecrypt.py")
        zf.write("../../src/main/res/sharedconstants.py", "src/main/res/sharedconstants.py")
        zf.write("../../src/main/res/__init__.py", "src/main/res/__init__.py")
        zf.write("../../src/main/__init__.py", "src/main/__init__.py")
        zf.write("../../src/__init__.py", "src/__init__.py")
