# Pro Asset README file

Notes from Rob

To deploy the Lambda, you hit the Run button (the triangular Play button next to Deploy, in IntelliJ).

In order for this to work, you need these parameters in the deploy Configuration:

```text
-p pro-asset -d thorntech-pgp-lambda-deploy -t DecryptedTargetBucket=thorntech-sftpgw-pgp-done EncryptedSourceBucket=thorntech-sftpgw-pgp-encrypted PgpKeyLocation=thorntech-pgp-keys PgpPassphrase="********" PgpKeyName=thorntech-key.asc
```

This custom configuration is committed to the ProAsset branch. 
Josh is working on Master to prepare this for a blob post.

Important note: the `PgpPassphrase` is not set in the committed code, which is a security issue. You will need to monkey patch this parameter in, prior to deploying. Otherwise, the deployment will fail, saying that the `PgpPassphrase` is missing.

Also, line 94 in `deploy.py` is commented out (the line that creates the bucket). This command is not idempotent, so subsequent runs will fail. Need to remember to comment this out on re-deploys, and uncomment on new deploys.