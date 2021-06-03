import boto3
import json
import lzma
import os
from logging import getLogger


logger = getLogger(__name__)


class User(object):
    """Retrieve the ldap users from S3 and process."""
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
            os.getenv('CIS_S3_BUCKET_NAME', 'cache.ldap.sso.mozilla.com'),
            os.getenv('CIS_LDAP_JSON_FILE', 'ldap_users.json.xz')
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

        for email in self.ldap_json:
            if email.split('@')[1] in self.email_suffix_whitelist:
                emails.append('{}@gcp.infra.mozilla.com'.format(email.split('@')[0]))
        return emails

    def to_gsuite_account_structure(self):
        users = []

        if self.ldap_json is None:
            self._get_ldap_json()

        for email in self.ldap_json:
            try:
                person = self.ldap_json[email]
                first_name = person['first_name']
                last_name = person['last_name']

                if email.split('@')[1] in self.email_suffix_whitelist:
                    logger.debug('Adding user: {} to the list of potential accounts.'.format(person))
                    users.append(
                        {
                            'first_name': first_name,
                            'last_name': last_name,
                            'primary_email': '{}@gcp.infra.mozilla.com'.format(email.lower().split('@')[0])
                        }
                    )
            except TypeError as e:
                logger.error('Could not process user: {} due to: {}.'.format(person, e))
        return users
