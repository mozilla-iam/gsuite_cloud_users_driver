

class TestDirectory(object):
    def test_object_init(self):
        from gsuite_cloud_users_driver import cloud

        directory = cloud.Directory()
        res = directory._get_keyfile_dict()
        assert res is not None

        directory._discover_service()
