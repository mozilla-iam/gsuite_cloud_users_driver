import logging
import sys
from googleapiclient.http import HttpError
from cloud import Directory
from ldap import User


def setup_logging():
    logger = logging.getLogger()
    for h in logger.handlers:
        logger.removeHandler(h)
    h = logging.StreamHandler(sys.stdout)
    FORMAT = '%(message)s'
    h.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    return logger


# Users that are exempt from interaction by this driver.
user_whitelist = [
    'iam-robot@gcp.infra.mozilla.com',
    'super-admin@gcp.infra.mozilla.com',
    'gene-owner@gcp.infra.mozilla.com',
    'bpitts-owner@gcp.infra.mozilla.com',
    'elim-owner@gcp.infra.mozilla.com',
]


def handle(event=None, context=None):
    logger = setup_logging()
    logger.info('Beginning a run of the mozilla-iam google cloud user driver.')
    ldap_users = User()
    directory = Directory()
    directory.user_whitelist = user_whitelist
    potential_gsuite_accounts = ldap_users.to_gsuite_account_structure()
    ldap_user_emails = ldap_users.to_emails(ldap_users.all)
    current_google_cloud_users = directory.all_emails()

    additions = []
    disables = []

    for user in potential_gsuite_accounts:
        email = user.get('primary_email')
        if email not in current_google_cloud_users and email not in user_whitelist:
            additions.append(user)
        else:
            logger.debug('Skipping user {} because they already exist in GCP.'.format(user))

    logger.info('{} potential accounts, with {} existing GCP accounts'.format(len(potential_gsuite_accounts), len(current_google_cloud_users)))

    for email in current_google_cloud_users:
        if email not in ldap_user_emails and email not in user_whitelist:
            disables.append(email)
        else:
            logger.debug('Skipping user {} because this user exists in LDAP or is whitelisted.'.format(email))

    logger.info(
        'Users collected the driver will create: {} and disable: {} users.'.format(len(additions), len(disables))
    )

    for user in additions:
        logger.info("Creating account for: {}".format(user.get('primary_email')))
        try:
            directory.create(user)
        except HttpError as error:
            if 'Entity already exists' in str(error):
                # We want to know about it, but still want to continue
                # for users that previously existed, were suspended, and now show up in ldap
                logger.error("User already exists in gcp: {}".format(user))
            else:
                raise error

    for email in disables:
        logger.info("Disabling account for: {}".format(email))
        try:
            directory.disable(email)
        except HttpError as error:
            if 'Not Authorized to access this resource/api' in str(error):
                # We want to know about it, but still want to continue
                # for users that we can't disable (admins)
                logger.error("Unable to disable user: {}".format(email))
            else:
                raise error

    logger.info('Infra GCP cloud users driver run complete.')

    return 200


if __name__ == '__main__':
    handle()
