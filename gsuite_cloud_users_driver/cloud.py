import boto3
import json
import uuid
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
from logging import getLogger


logger = getLogger(__name__)


class Directory(object):
    def __init__(self):
        self.auth = None
        self.scope = "https://www.googleapis.com/auth/admin.directory.user"

        # Run _discover_service() on creation, so it doesn't need to be called
        # by every single function invocation
        self._discover_service()

    def _discover_service(self):
        store = ServiceAccountCredentials.from_json_keyfile_dict(
            keyfile_dict=self._get_keyfile_dict(), scopes=self.scope
        )
        delegated_credentials = store.create_delegated(
            "iam-robot@gcp.infra.mozilla.com"
        )
        creds = delegated_credentials.authorize(http=Http())
        self.service = discovery.build("admin", "directory_v1", http=creds)

        return self.service

    def _get_keyfile_dict(self):
        ssm = boto3.client("ssm", region_name="us-west-2")
        result = ssm.get_parameter(
            Name="/iam/gcp/cloud-account-driver", WithDecryption=True
        )
        return json.loads(result["Parameter"]["Value"])

    def all_users(self):
        users = []
        results = self.service.users().list(domain="gcp.infra.mozilla.com").execute()

        # process all but the last page
        while results.get("nextPageToken", None) is not None:
            for user in results.get("users", []):
                if user["suspended"] == False:
                    users.append(user)

            results = (
                self.service.users()
                .list(
                    domain="gcp.infra.mozilla.com",
                    pageToken=results.get("nextPageToken"),
                )
                .execute()
            )

        # process the last page, or the first page if there is only one
        for user in results.get("users", []):
            if user["suspended"] == False:
                users.append(user)

        logger.info("Total active GCP users : {}".format(len(users)))

        return users

    def all_emails(self):
        return [user["primaryEmail"] for user in self.all_users()]

    def update_user(self, primary_email, body):
        result = self.service.users().update(userKey=primary_email, body=body).execute()
        return result

    def create(self, user_dict):
        email_prefix = user_dict["primary_email"].split("@")[0]
        body = {
            "name": {
                "givenName": email_prefix[0],
                "fullName": email_prefix,
                "familyName": email_prefix[1:],
            },
            "primaryEmail": "{}@gcp.infra.mozilla.com".format(email_prefix),
            "password": uuid.uuid4().hex,
            "agreedToTerms": True,
        }
        try:
            result = self.service.users().insert(body=body).execute()
        except HttpError as e:
            if e.reason == "Entity already exists.":
                email = body.pop("primaryEmail")
                result = self.update_user(email, body)
            else:
                print(e)

        return result

    def disable(self, user):
        body = {
            "suspended": True,
            "suspensionReason": "The user no longer exists in ldap and was disabled by mozilla-iam.",
        }

        return self.service.users().patch(userKey=user, body=body).execute()

    def delete(self, user):
        return self.service.users().delete(userKey=user).execute()
