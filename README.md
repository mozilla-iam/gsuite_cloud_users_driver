# GSuite Cloud Users Driver

The purpose of this driver is to ensure that all users with a getpocket.com, mozillafoundation.com, and mozilla.com
email have the ability to single-sign-on into GCP and manage the lifecycle of those accounts.

# Deployment

```bash
$ $(maws)   # become MAWS-Admin in mozilla-iam
$ npm install
$ cd gsuite_cloud_users_driver
$ ../node_modules/.bin/serverless deploy
```

Verify that the driver has been updated properly in Lambda. Note that
you can monitor the logs from this Lambda with:

```bash
$ awslogs get --start 10m --watch /aws/lambda/gcp-cloud-users-prod-driver
```

# See Also
* [Mana documentation](https://mana.mozilla.org/wiki/pages/viewpage.action?spaceKey=SECURITY&title=Google+Cloud+Platform+GCP+gcp.infra.mozilla.com)
