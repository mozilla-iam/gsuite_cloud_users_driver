import boto3
import json
import lzma
from gsuite_cloud_users_driver import common
from logging import getLogger


logger = getLogger(__name__)


class User(object):
    """Retrieve the ldap users from the ldap.xz.json and process."""
    def __init__(self):
        self.s3 = None
        self.ldap_json = None
        self.email_suffix_whitelist = ['mozilla.com', 'mozillafoundation.org', 'getpocket.com']

    def _connect_s3(self):
        if self.s3 is None:
            self.s3 = boto3.resource('s3')

    def _get_ldap_json(self):
        self._connect_s3()
        obj = self.s3.Object(
            common.S3_BUCKET_NAME,
            'ldap-full-profile-v2.json.xz'
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
                    logger.info('Adding user: {} to the list of potential accounts.'.format(person))
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
        return user.get('primary_email')['value'].lower()

    def _record_to_first_name(self, user):
        return user.get('first_name')['value']

    def _record_to_last_name(self, user):
        return user.get('last_name')['value']


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
            user_groups = self.users[user]['access_information']['ldap']['values']
            for group in user_groups:
                proposed_group = {'group': group, 'members': []}
                if proposed_group not in self.groups:
                    self.groups.append(proposed_group)

    def _populate_membership(self):
        for group in self.groups:
            group_name = group['group']

            # Go find all the members
            for user in self.users:
                if group_name in self.users[user]['access_information']['ldap']['values']:
                    idx = self.groups.index(group)
                    self.groups[idx]['members'].append(self._record_to_primary_email(self.users[user]))

    def _record_to_primary_email(self, user):
        return '{}@gcp.infra.mozilla.com'.format(user.get('primary_email')['value'].lower().split('@')[0])
