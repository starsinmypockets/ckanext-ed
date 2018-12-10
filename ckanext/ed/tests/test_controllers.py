from nose.tools import assert_raises

from ckan.lib.helpers import url_for
from ckan.plugins import toolkit
from ckan.tests import helpers, factories

class TestController(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):

        helpers.reset_db()
        super(TestController, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        super(TestController, cls).teardown_class()
        helpers.reset_db()

    def setup(self):
        super(TestController, self).setup()
        sysadmin = factories.Sysadmin()
        self.extra_environ = {'REMOTE_USER': sysadmin['name'].encode('ascii')}

    def test_requests_403_for_anonimous_users(self):
        app = self._get_test_app()

        with assert_raises(toolkit.NotAuthorized) as e:
            app.get(url=url_for('dashboard.requests'), status=403)


    def test_requests_tab_not_appears_for_member_on_dashboard(self):
        app = self._get_test_app()
        member = factories.User()
        factories.Organization(users=[{'name': member['name'], 'capacity': 'reader'}])

        extra_environ = {'REMOTE_USER': member['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert '<a href="/dashboard/requests">Requests</a>' not in resp

    def test_requests_tab_not_appears_for_editor_on_dashboard(self):
        app = self._get_test_app()
        editor = factories.User()
        factories.Organization(users=[{'name': editor['name'], 'capacity': 'editor'}])

        extra_environ = {'REMOTE_USER': editor['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert '<a href="/dashboard/requests">Pending dataset requests (0)</a>' not in resp

    def test_requests_tab_appears_for_admin_on_dashboard(self):
        app = self._get_test_app()
        editor = factories.User()
        factories.Organization(users=[{'name': editor['name'], 'capacity': 'admin'}])

        extra_environ = {'REMOTE_USER': editor['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert '<a href="/dashboard/requests">Pending dataset requests (0)</a>' in resp, resp

    def test_requests_tab_appears_for_sysadmin_on_dashboard(self):
        app = self._get_test_app()
        sysadmin = factories.Sysadmin()
        factories.Organization(users=[{'name': sysadmin['name'], 'capacity': 'sysadmin'}])

        extra_environ = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert '<a href="/dashboard/requests">Pending dataset requests (0)</a>' in resp

    def test_pending_datasets_show_up_on_dashboard(self):
        app = self._get_test_app()
        # Create Users
        editor = factories.User()
        admin = factories.User()
        factories.Organization(
            users=[
                {'name': admin['name'], 'capacity': 'admin'},
                {'name': editor['name'], 'capacity': 'editor'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        # Create Datasets
        context = {'user': editor['name']}
        data_dict = _create_dataset_dict('test-pending-1', 'us-ed-1')
        helpers.call_action('package_create', context, **data_dict)

        extra_environ = {'REMOTE_USER': admin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert 'TEST-PENDING-1' in resp, resp

    def test_non_pending_datasets_do_not_show_up_on_dashboard(self):
        app = self._get_test_app()
        # Create Users
        editor = factories.User()
        admin = factories.User()
        factories.Organization(
            users=[
                {'name': admin['name'], 'capacity': 'admin'},
                {'name': editor['name'], 'capacity': 'editor'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        # Create Datasets
        context = {'user': admin['name']}
        data_dict_1 = _create_dataset_dict('test-pending-1', 'us-ed-1')
        helpers.call_action('package_create', context, **data_dict_1)
        context = {'user': editor['name']}
        data_dict_2 = _create_dataset_dict('test-pending-2', 'us-ed-1')
        helpers.call_action('package_create', context, **data_dict_2)

        extra_environ = {'REMOTE_USER': admin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        # By admin should not be there
        assert 'TEST-PENDING-1' not in resp
        # By editor should be there
        assert 'TEST-PENDING-2' in resp

    def test_pending_datasets_from_other_office_dont_show_up_for_admin(self):
        app = self._get_test_app()
        # Create Users
        editor_native = factories.User()
        editor_forigner = factories.User()
        admin = factories.User()
        factories.Organization(
            users=[
                {'name': admin['name'], 'capacity': 'admin'},
                {'name': editor_native['name'], 'capacity': 'editor'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        factories.Organization(
            users=[{'name': editor_forigner['name'], 'capacity': 'editor'}],
            name='us-ed-2',
            id='us-ed-2'
        )
        # Create Datasets
        context = {'user': editor_native['name']}
        data_dict_native = _create_dataset_dict('test-pending-native', 'us-ed-1')
        helpers.call_action('package_create', context, **data_dict_native)

        context = {'user': editor_forigner['name']}
        data_dict_forign = _create_dataset_dict('test-pending-forign', 'us-ed-2')
        helpers.call_action('package_create', context, **data_dict_forign)

        extra_environ = {'REMOTE_USER': admin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert 'TEST-PENDING-FORIGN' not in resp
        assert 'TEST-PENDING-NATIVE' in resp


    def test_pending_private_datasets_show_up_on_dashboard(self):
        app = self._get_test_app()
        # Create Users
        editor = factories.User()
        admin = factories.User()
        factories.Organization(
            users=[
                {'name': admin['name'], 'capacity': 'admin'},
                {'name': editor['name'], 'capacity': 'editor'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        # Create Dataset
        context = {'user': editor['name']}
        data_dict = _create_dataset_dict('test-pending-private', 'us-ed-1', private=True)
        helpers.call_action('package_create', context, **data_dict)

        extra_environ = {'REMOTE_USER': admin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert 'TEST-PENDING-PRIVATE' in resp, resp


def _create_dataset_dict(package_name, office_name='us-ed', private=False):
    return {
        'name': package_name,
        'contact_name': 'Stu Shepard',
        'program_code': '321',
        'access_level': 'public',
        'bureau_code': '123',
        'contact_email': '%s@email.com' % package_name,
        'notes': 'notes',
        'owner_org': office_name,
        'title': package_name.upper(),
        'identifier': 'identifier',
        'private': private
    }
