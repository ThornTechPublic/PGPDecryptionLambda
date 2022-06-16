## Intro
* Every test in this list should be run locally and through the Azure portal
* In the future, make a script or hard code it so that each test uses different files and can be compared to checksums
* In the future these should be automated

## Normal Tests
1. Single upload of encrypted file, key in same container + not in folder
2. Single upload of non-encrypted file, key in same container + not in folder
3. Multiple upload all encrypted, key in same container + not in folder

## Folder Tests
4. Single upload of encrypted file, key in diff container + IS in folder
5. Multiple upload of encrypted files, key in diff container + IS in folder
6. Multiple upload of encrypted files to folder, key in diff container + IS in folder

## Zip Tests
7. Single upload of zip file of one encrypted file, key in diff container + in folder
8. Single upload of zip file of multiple mixed files, key in diff container + in folder
9. Multiple upload of zip files + encrypted files + non-encrypted files, key in diff container + in folder
10. Single upload of zip file to folder, key in diff container + in folder
11. Multiple upload of zip files + encrypted files + non-encrypted files to folder, key in diff container + in folder
12. Single upload of encrypted zip file of multiple files, key in diff container + in folder


## Image Version Scores
* v1.0.0: 2
* v1.1.0: 6
* v1.2.0: 