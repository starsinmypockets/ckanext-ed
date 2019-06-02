import mock

from nose.tools import assert_raises

from ckan import model
from ckan.lib.helpers import url_for
from ckan.lib.search import rebuild
from ckan.logic import NotFound
from ckan.plugins import toolkit
from ckan.tests import helpers, factories

class TestBasicControllers(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        helpers.reset_db()
        super(TestBasicControllers, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        super(TestBasicControllers, cls).teardown_class()
        helpers.reset_db()

    def setup(self):
        super(TestBasicControllers, self).setup()
        helpers.reset_db()
        self.sysadmin = factories.Sysadmin()
        self.pkg = 'test-dataset-base'
        self.orgname = 'us-ed-base'
        factories.Organization(name=self.orgname, id=self.orgname)
        context = _create_context(self.sysadmin)
        data_dict = _create_dataset_dict(self.pkg, self.orgname, private=False)
        self.package = helpers.call_action('package_create', context, **data_dict)
        self.envs = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.app = self._get_test_app()

    def test_home_page_is_ok_for_anonimous(self):
        resp = self.app.get(url=url_for('/'))
        assert resp.status_int == 200

    def test_home_page_is_ok_for_sysadmin(self):
        resp = self.app.get(url=url_for('/'), extra_environ=self.envs)
        assert resp.status_int == 200

    def test_dataset_page_is_ok_for_anonimous(self):
        resp = self.app.get(url=url_for('/dataset'))
        assert resp.status_int == 200

    def test_dataset_page_is_ok_for_sysadmin(self):
        resp = self.app.get(url=url_for('/dataset'), extra_environ=self.envs)
        assert resp.status_int == 200

    def test_org_page_is_ok_for_anonimous(self):
        resp = self.app.get(url=url_for('/organization/%s' % self.orgname))
        assert resp.status_int == 200

    def test_org_page_is_ok_for_sysadmin(self):
        resp = self.app.get(url=url_for('/organization/%s' % self.orgname), extra_environ=self.envs)
        assert resp.status_int == 200

    def test_pakage_page_is_ok_for_anonimous(self):
        resp = self.app.get(url=url_for('/dataset/%s' % self.pkg))
        assert resp.status_int == 200

    def test_pakage_page_is_ok_for_sysadmin(self):
        resp = self.app.get(url=url_for('/dataset/%s' % self.pkg), extra_environ=self.envs)
        assert resp.status_int == 200


class TestNewResourceController(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()
        super(TestNewResourceController, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        super(TestNewResourceController, cls).teardown_class()
        helpers.reset_db()

    def setup(self):
        super(TestNewResourceController, self).setup()
        helpers.reset_db()
        self.sysadmin = factories.Sysadmin()
        self.pkg = 'test-dataset-1'
        self.orgname = 'us-ed-docs'
        factories.Organization(name=self.orgname, id=self.orgname)
        context = _create_context(self.sysadmin)
        data_dict = _create_dataset_dict(self.pkg, self.orgname, private=False)
        data_dict.update(state='draft')
        self.package = helpers.call_action('package_create', context, **data_dict)
        self.envs = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}

    def test_create_new_resource_has_add_docs_button(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/new_resource/%s' % self.pkg), extra_environ=self.envs)
        assert 'Next: Add Documentation' in resp

    def test_create_doc_has_add_previous_button(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/new_doc/%s' % self.pkg), extra_environ=self.envs)
        assert 'Previous' in resp

    def test_create_doc_has_add_another_button(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/new_doc/%s' % self.pkg), extra_environ=self.envs)
        assert 'Save &amp; add another' in resp

    def test_create_doc_has_add_finish_button(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/new_doc/%s' % self.pkg), extra_environ=self.envs)
        assert 'Finish' in resp


class TestDocumentationController(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()
        super(TestDocumentationController, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        super(TestDocumentationController, cls).teardown_class()
        helpers.reset_db()

    def setup(self):
        super(TestDocumentationController, self).setup()
        helpers.reset_db()
        self.sysadmin = factories.Sysadmin()
        self.pkg = 'test-dataset-for-docs'
        self.orgname = 'us-ed-docs'
        factories.Organization(name=self.orgname, id=self.orgname)
        self.context = _create_context(self.sysadmin)
        data_dict = _create_dataset_dict(self.pkg, self.orgname, private=False)
        data_dict.update(resources=[
            {'name': 'this-is-regular-resource', 'url': '', 'description': 'resouce', 'format': 'pdf', 'resource_type': 'regular-resource'},
            {'name': 'this-is-doc', 'url': '', 'description': 'doc', 'format': 'pdf', 'resource_type': 'doc'},
            {'name': 'this-is-pinned-doc', 'url': '', 'description': 'doc', 'format': 'pdf', 'resource_type': 'doc', 'pinned': 'True'}
        ])
        # data_dict.update(state='draft')
        self.package = helpers.call_action('package_create', self.context, **data_dict)
        self.envs = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}

    def test_documentation_tab_appears_on_dataset_page(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/%s' % self.pkg), extra_environ=self.envs)
        assert 'Docs' in resp

    def test_dataset_tab_has_no_doc_resources(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/%s' % self.pkg), extra_environ=self.envs)
        assert 'this-is-doc' not in resp

    def test_documentation_tab_has_work_ok_if_anonymous(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/docs/%s' % self.pkg))
        assert resp.status_int == 200

    def test_documentation_tab_has_no_regulars_resources(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/docs/%s' % self.pkg), extra_environ=self.envs)
        assert 'this-is-regular-resource' not in resp, resp
        assert 'this-is-doc' in resp

    def test_documentation_tab_has_reorder_button(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/docs/%s' % self.pkg), extra_environ=self.envs)
        assert 'reorder' in resp, resp

    def test_documentation_tab_has_no_add_new_doc_button_for_anonymous(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/docs/%s' % self.pkg))
        assert 'Add new doc' not in resp, resp

    def test_documentation_tab_has_no_explore_button_if_it_is_edit_mode(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/docs/%s?edit=true' % self.pkg), extra_environ=self.envs)
        assert 'Explore' not in resp

    def test_documentation_tab_has_pin_button(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/docs/%s' % self.pkg), extra_environ=self.envs)
        assert 'Pin' in resp

    def test_documentation_tab_has_no_pin_button_for_anonymous(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/docs/%s' % self.pkg))
        assert 'Pin' not in resp

    def test_documentation_tab_has_unpin_button(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/docs/%s' % self.pkg), extra_environ=self.envs)
        assert 'Unpin' in resp

    def test_documentation_tab_has_no_unpin_button_for_anonymous(self):
        app = self._get_test_app()
        resp = app.get(url=url_for('/dataset/docs/%s' % self.pkg))
        assert 'Unpin' not in resp

    def test_pin_works(self):
        pinned_res_id = None
        unpinned_res_id = None
        for res in self.package['resources']:
            if res.get('pinned') == 'True':
                pinned_res_id = res['id']
            else:
                unpinned_res_id = res['id']

        app = self._get_test_app()
        resp = app.get(
            url=url_for('/dataset/docs/{}/pin/{}'.format(self.pkg, unpinned_res_id)),
            extra_environ=self.envs
        )
        unpinned_resource = helpers.call_action('resource_show', self.context, **{'id': pinned_res_id})
        pinned_resource = helpers.call_action('resource_show', self.context, **{'id': unpinned_res_id})
        assert pinned_resource['pinned'] == 'True', pinned_resource
        assert unpinned_resource['pinned'] == 'False', pinned_resource

    def test_unpin_works(self):
        pinned_res_id = self.package['resources'][0]['id']
        app = self._get_test_app()
        app.get(
            url=url_for('/dataset/docs/{}/pin/{}'.format(self.pkg, pinned_res_id)),
            extra_environ=self.envs
        )
        resp = app.get(
            url=url_for('/dataset/docs/{}/unpin/{}'.format(self.pkg, pinned_res_id)),
            extra_environ=self.envs
        )
        resource = helpers.call_action('resource_show', self.context, **{'id': pinned_res_id})
        assert resource['pinned'] == 'False'


class TestStateUpdateController(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):

        helpers.reset_db()
        super(TestStateUpdateController, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        super(TestStateUpdateController, cls).teardown_class()
        helpers.reset_db()

    def setup(self):
        super(TestStateUpdateController, self).setup()
        self.pkg = 'test-dataset-1'
        helpers.reset_db()
        rebuild()
        factories.User(name='george', id='george')
        factories.User(name='john', id='john')
        factories.User(name='paul', id='paul')
        factories.Organization(
            users=[
                {'name': 'george', 'capacity': 'admin'},
                {'name': 'john', 'capacity': 'editor'},
                {'name': 'paul', 'capacity': 'reader'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        # Dataset created by factories seem to use sysadmin so approval_state
        # forced to be "approved". Creating packages this way to avoid that
        context = {'user': 'john'}
        data_dict = _create_dataset_dict(self.pkg, 'us-ed-1', private=True)
        self.package = helpers.call_action('package_create', context, **data_dict)


    def test_dataset_reject_403_for_anonymous_users(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            app.get(url=url_for('/dataset-publish/{0}/reject'.format(self.package['id']), status=403))

    def test_dataset_reject_403_for_member(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'paul'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/reject'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    def test_dataset_reject_403_for_editor(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'john'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/reject'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_reject_302_for_admin(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/reject'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        assert resp.status_int, 302

    def test_dataset_approve_403_for_anonymous_users(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            app.get(url=url_for('/dataset-publish/{0}/approve'.format(self.package['id']), status=403))

    def test_dataset_approve_403_for_member(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'paul'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/approve'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    def test_dataset_approve_403_for_editor(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'john'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/approve'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_approve_302_for_admin(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/approve'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        assert resp.status_int, 302

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_approve_and_publish_for_admin(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        updated = helpers.call_action('package_show', {'user': 'george'}, **{'id': self.package['id']})
        # Make sure it's private before call
        assert updated['private']
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/approve?make_public=true'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        updated = helpers.call_action('package_show', {'user': 'george'}, **{'id': self.package['id']})
        assert not updated['private']

    def test_dataset_resubmit_403_for_anonymous_users(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            app.get(url=url_for('/dataset-publish/{0}/resubmit'.format(self.package['id']), status=403))

    def test_dataset_resubmit_403_for_member(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'paul'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/resubmit'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_resubmit_302_for_editor(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'john'}
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/resubmit'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        assert resp.status_int, 302

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_resubmit_302_for_admin(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/resubmit'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        assert resp.status_int, 302


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

def _create_context(user):
    return {'model': model, 'user': user['name']}
