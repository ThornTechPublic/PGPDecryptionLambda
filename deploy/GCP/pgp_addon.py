import random


def generate_config(context):
    resources = [{
        "name": f"{context.env['deployment']}-{random.randint(0,100)}",
        "type": "gcp-types/cloudfunctions-v1:projects.locations.functions",
        "properties": {
            "runtime": context.properties["runtime"],
            "entryPoint": "invoke",
            "parent": f"projects/{context.env['project']}/locations/{context.properties['region']}",
            "function": f"my-{context.env['deployment']}",
            "source_archive_url": "gs://pgpkeybucket54884/pgpGoogleArchive.zip",
            "availableMemoryMb": 2048,
            "serviceAccountEmail": "pgpfunction-service-account@sftp-gateway.iam.gserviceaccount.com",
            "environmentVariables": {
                "PGP_KEY_LOCATION": "pgpkeybucket54884",
                "PGP_KEY_NAME": "keyfolder/private.asc",
                "PGP_PASSPHRASE": "IAMAROBOT",
                "DECRYPTED_DONE_LOCATION": "pgpdecryptedbucket54884",
                "ARCHIVE": r"\1/archive/\2"
            },
            "eventTrigger": {
                "resource": f"projects/{context.env['project']}/buckets/pgpencryptedbucket54884",
                "eventType": "google.storage.object.finalize"
            }
        }
    }]
    return {"resources": resources}

