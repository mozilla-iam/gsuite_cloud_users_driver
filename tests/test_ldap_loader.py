

class TestLDAP(object):
    def test_s3_data_retieved(self):
        from gsuite_cloud_users_driver import ldap
        ldap_user = ldap.User()
        ldap_user._get_ldap_json()
        assert ldap_user.ldap_json is not None
        all = ldap_user.all
        assert all is not None
        emails = ldap_user.to_emails(all)
        assert emails is not None
        gsuite_profiles = ldap_user.to_gsuite_account_structure()
        assert gsuite_profiles is not None

    def test_grouplist(self):
        from gsuite_cloud_users_driver import ldap
        ldap_user = ldap.User()
        all = ldap_user.all
        groups = ldap.Group(all)
        grouplist = groups.all
        assert grouplist is not None
