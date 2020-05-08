import boto3
import json
import lzma
import os
from logging import getLogger


logger = getLogger(__name__)


class User(object):
    """Retrieve the ldap users from the ldap.xz.json and process."""
    def __init__(self):
        self.s3 = None
        self.ldap_json = None
        self.email_suffix_whitelist = ['mozilla.com', 'mozillafoundation.org', 'getpocket.com']

    def _assume_role(self):
        logger.info('Assuming role for pulling ldap data.')
        client = boto3.client('sts')
        response = client.assume_role(
            RoleArn=os.getenv(
                'LDAP_ASSUME_ROLE_ARN',
                'arn:aws:iam::371522382791:role/cis-gsuite-users-driver'
            ),
            RoleSessionName='gcp-cloud-driver',
        )
        return response['Credentials']

    def _connect_s3(self):
        if self.s3 is None:
            assume_role = self._assume_role()
            self.s3 = boto3.resource(
                's3',
                aws_access_key_id=assume_role['AccessKeyId'],
                aws_secret_access_key=assume_role['SecretAccessKey'],
                aws_session_token=assume_role['SessionToken']
            )

    def _get_ldap_json(self):
        self._connect_s3()
        obj = self.s3.Object(
            os.getenv('CIS_S3_BUCKET_NAME', 'cis-ldap2s3-publisher-data'),
            os.getenv('CIS_LDAP_JSON_FILE', 'ldap-full-profile.json.xz')
        )

        tarred_json = bytes(obj.get()["Body"].read())
        ldap_json = json.loads(lzma.decompress(tarred_json))
        self.ldap_json = ldap_json

    @property
    def all(self):
        if self.ldap_json is None:
            self._get_ldap_json()

        return self.ldap_json

    def to_emails(self, users):
        """takes profilev2 ldap_json and turns into a list of emails."""
        emails = []

        if self.ldap_json is None:
            self._get_ldap_json()

        for person in self.ldap_json:
            email = self._record_to_primary_email(self.ldap_json[person])
            if email.split('@')[1] in self.email_suffix_whitelist:
                emails.append('{}@gcp.infra.mozilla.com'.format(email.split('@')[0]))
        return emails

    def to_gsuite_account_structure(self):
        users = []

        if self.ldap_json is None:
            self._get_ldap_json()

        for person in self.ldap_json:
            try:
                email = self._record_to_primary_email(self.ldap_json[person])
                first_name = self._record_to_first_name(self.ldap_json[person])
                last_name = self._record_to_last_name(self.ldap_json[person])

                if email.split('@')[1] in self.email_suffix_whitelist:
                    logger.debug('Adding user: {} to the list of potential accounts.'.format(person))
                    users.append(
                        {
                            'first_name': first_name,
                            'last_name': last_name,
                            'primary_email': '{}@gcp.infra.mozilla.com'.format(email.split('@')[0])
                        }
                    )
            except TypeError as e:
                logger.error('Could not process user: {} due to: {}.'.format(person, e))
        return users

    def _record_to_primary_email(self, user):
        return user.get('primaryEmail').lower()

    def _record_to_first_name(self, user):
        return user.get('firstName')

    def _record_to_last_name(self, user):
        return user.get('lastName')


# TODO: Delete this? It doesn't seem to be used anywhere.
class Group(object):
    def __init__(self, users):
        self.users = users
        self.groups = []

    @property
    def all(self):
        """Convert the list of users with emails to a groups data structure."""
        if len(self.groups) == 0:
            self._generate_grouplist()
            self._populate_membership()
        return self.groups

    def _generate_grouplist(self):
        for user in self.users:
            # This is for the full profile syntax
            user_groups = self.users[user]['access_information']['ldap']['values']
            # TODO replace with something like except get only ldap groups maybe?
            # user_groups = self.users[user]['groups']
            for group in user_groups:
                proposed_group = {'group': group, 'members': []}
                if proposed_group not in self.groups:
                    self.groups.append(proposed_group)

    def _populate_membership(self):
        for group in self.groups:
            group_name = group['group']

            # Go find all the members
            for user in self.users:
                # This is for the full profile syntax
                # TODO replace with something like except get only ldap groups maybe?
                # if group_name in self.users[user]['groups']:
                if group_name in self.users[user]['access_information']['ldap']['values']:
                    idx = self.groups.index(group)
                    self.groups[idx]['members'].append(self._record_to_primary_email(self.users[user]))

    def _record_to_primary_email(self, user):
        return '{}@gcp.infra.mozilla.com'.format(user.get('primary_email')['value'].lower().split('@')[0])
