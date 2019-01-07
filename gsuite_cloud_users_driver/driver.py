import logging
import sys
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
    'super-admin@gcp.infra.mozilla.com',
    'iam-robot@gcp.infra.mozilla.com',
    'jgmize-owner@gcp.infra.mozilla.com',
    'akrug-owner@gcp.infra.mozilla.com'
]


def handle(event=None, context={}):
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
        if user.get('primary_email') not in current_google_cloud_users:
            additions.append(user)
        else:
            logger.info('Skipping user {} because they are whitelisted.'.format(user))


    for email in current_google_cloud_users:
        if email not in ldap_user_emails and email not in user_whitelist:
            disables.append(email)
        else:
            logger.info('Skipping user {} because they are whitelisted.'.format(email))

    logger.info(
        'Users collected the driver will create: {} and disable: {} users.'.format(len(additions), len(disables))
    )

    for user in additions:
        directory.create(user)
        logger.info('Account created for: {}'.format(user['primary_email']))

    for email in disables:
        directory.disable(email)
        logger.info('Account disabled for: {}'.format(email))

    logger.info('Driver run complete.')
    return 200

if __name__ == '__main__':
    handle()
