import boto3
import json
import uuid
from apiclient import discovery
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials


class Directory(object):
    def __init__(self):
        self.auth = None
        self.scope = 'https://www.googleapis.com/auth/admin.directory.user'
        self.service = None
        self.user_whitelist = [
            'super-admin@gcp.infra.mozilla.com',
            'iam-robot@gcp.infra.mozilla.com'
        ]

    def _discover_service(self):
        if self.service is None:
            store = ServiceAccountCredentials.from_json_keyfile_dict(
                keyfile_dict=self._get_keyfile_dict(), scopes=self.scope
            )
            delegated_credentials = store.create_delegated('iam-robot@gcp.infra.mozilla.com')
            creds = delegated_credentials.authorize(http=Http())
            service = discovery.build('admin', 'directory_v1', http=creds)
            self.service = service
        return self.service

    def _get_keyfile_dict(self):
        ssm = boto3.client('ssm', region_name='us-west-2')
        result = ssm.get_parameter(Name='/iam/gcp/cloud-account-driver', WithDecryption=True)
        return json.loads(result['Parameter']['Value'])

    def all_users(self):
        users = []
        self._discover_service()
        results = self.service.users().list(domain='gcp.infra.mozilla.com').execute()

        while results.get('nextPageToken', None) is not None:
            for user in results.get('users'):
                users.append(user)

            results = self.service.users().list(
                domain='gcp.infra.mozilla.com', pageToken=results.get('nextPageToken')
            ).execute()

        for user in results.get('users'):
            users.append(user)

        return users

    def all_emails(self):
        users = self.all_users()
        emails = []
        for user in users:
            emails.append(user['primaryEmail'])
        return emails

    def create(self, user_dict):
        self._discover_service()
        body = {
            'name': {
                'givenName': user_dict['first_name'],
                'fullName': '{} {}'.format(user_dict['first_name'], user_dict['last_name']),
                'familyName': user_dict['last_name']
            },
            'primaryEmail': '{}@gcp.infra.mozilla.com'.format(user_dict['primary_email'].split('@')[0]),
            'password': self._generate_random_password(),
            'agreedToTerms': True
        }
        return self.service.users().insert(body=body).execute()

    def _generate_random_password(self):
        return uuid.uuid4().hex

    def disable(self, user):
        self._discover_service()
        body = {
            'suspended': True,
            'suspensionReason': 'The user no longer exists in ldap and was disabled by mozilla-iam.'
        }

        if user['primary_email'] not in self.user_whitelist:
            return self.service.users().patch(userKey=user['primary_email'], body=body).execute()

    def delete(self, user):
        self._discover_service()

        if user['primary_email'] not in self.user_whitelist:
            return self.service.users().delete(userKey=user['primary_email']).execute()
