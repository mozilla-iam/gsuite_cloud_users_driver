import boto3
import json
import uuid
from apiclient import discovery
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
from logging import getLogger


logger = getLogger(__name__)


class Directory(object):
    def __init__(self):
        self.auth = None
        self.scope = 'https://www.googleapis.com/auth/admin.directory.user'

        # Run _discover_service() on creation, so it doesn't need to be called
        # by every single function invocation
        self._discover_service()

    def _discover_service(self):
        store = ServiceAccountCredentials.from_json_keyfile_dict(
            keyfile_dict=self._get_keyfile_dict(), scopes=self.scope
        )
        delegated_credentials = store.create_delegated('iam-robot@gcp.infra.mozilla.com')
        creds = delegated_credentials.authorize(http=Http())
        self.service = discovery.build('admin', 'directory_v1', http=creds)

        return self.service

    def _get_keyfile_dict(self):
        ssm = boto3.client('ssm', region_name='us-west-2')
        result = ssm.get_parameter(Name='/iam/gcp/cloud-account-driver', WithDecryption=True)
        return json.loads(result['Parameter']['Value'])

    def all_users(self):
        users = []
        results = self.service.users().list(domain='gcp.infra.mozilla.com').execute()

        # process all but the last page
        while results.get('nextPageToken', None) is not None:
            for user in results.get('users', []):
                if user['suspended'] == False:
                    users.append(user)

            results = self.service.users().list(
                domain='gcp.infra.mozilla.com', pageToken=results.get('nextPageToken')
            ).execute()

        # process the last page, or the first page if there is only one
        for user in results.get('users', []):
            if user['suspended'] == False:
                users.append(user)

        logger.info('Total active GCP users : {}'.format(len(users)))

        return users

    def all_emails(self):
        return [user['primaryEmail'] for user in self.all_users()]

    def create(self, user_dict):
        body = {
            'name': {
                'givenName': user_dict['first_name'],
                'fullName': '{} {}'.format(user_dict['first_name'], user_dict['last_name']),
                'familyName': user_dict['last_name']
            },
            'primaryEmail': '{}@gcp.infra.mozilla.com'.format(user_dict['primary_email'].split('@')[0]),
            'password': uuid.uuid4().hex,
            'agreedToTerms': True
        }

        return self.service.users().insert(body=body).execute()

    def disable(self, user):
        body = {
            'suspended': True,
            'suspensionReason': 'The user no longer exists in ldap and was disabled by mozilla-iam.'
        }
        
        return self.service.users().patch(userKey=user, body=body).execute()

    def delete(self, user):
        return self.service.users().delete(userKey=user).execute()
