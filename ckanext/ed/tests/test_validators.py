from nose.tools import assert_equals

from ckan import model
from ckan.plugins import toolkit
from ckan.tests import factories as core_factories
from ckan.tests.helpers import call_action, FunctionalTestBase, reset_db


class TestDocsValidators(FunctionalTestBase):
    def setup(self):
        reset_db()
        self.sysadmin = core_factories.Sysadmin()
        self.orgname = 'us-ed-docs'
        core_factories.Organization(name=self.orgname, id=self.orgname)

    def test_resource_type_validator_regular_resource(self):
        context = _create_context(self.sysadmin)
        resources = [{'name': 'doc', 'url': '', 'description': 'doc', 'format': 'pdf'}]
        data_dict = _create_dataset_dict('test-dataset-1', self.orgname, resources=resources)
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-1')
        assert dataset.get('resources')[0]['resource_type'] == 'regular-resource'

    def test_resource_type_validator_doc(self):
        context = _create_context(self.sysadmin)
        context.update(is_doc=True)
        resources = [{'name': 'doc', 'url': '', 'description': 'doc', 'format': 'pdf'}]
        data_dict = _create_dataset_dict('test-dataset-2', self.orgname, resources=resources)
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-2')
        assert dataset.get('resources')[0]['resource_type'] == 'doc'

    def test_resource_type_validator_not_modifies_if_type_is_present(self):
        context = _create_context(self.sysadmin)
        resources = [
            {'name': 'doc', 'url': '', 'description': 'doc', 'format': 'pdf', 'resource_type': 'doc'}
        ]
        data_dict = _create_dataset_dict('test-dataset-3', self.orgname, resources=resources)
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-3')
        assert dataset.get('resources')[0]['resource_type'] == 'doc'

    def test_resource_type_validator_not_modifies_doc_on_resource_update(self):
        context = _create_context(self.sysadmin)
        resources = [
            {'name': 'doc', 'url': '', 'description': 'doc', 'format': 'pdf', 'resource_type': 'doc'}
        ]
        data_dict = _create_dataset_dict('test-dataset-3a', self.orgname, resources=resources)
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-3a')
        data_to_update = {
            'id':dataset.get('resources')[0]['id'], 'name': 'doc', 'url': '',
            'description': 'doc', 'format': 'pdf'
        }
        updated = call_action('resource_update', context, **data_to_update)
        assert updated['resource_type'] == 'doc'

    def test_resource_type_validator_not_modifies_regular_resource_on_resource_update(self):
        context = _create_context(self.sysadmin)
        resources = [
            {'name': 'doc', 'url': '', 'description': 'doc', 'format': 'pdf', 'resource_type': 'regular-resource'}
        ]
        data_dict = _create_dataset_dict('test-dataset-3b', self.orgname, resources=resources)
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-3b')
        data_to_update = {
            'id':dataset.get('resources')[0]['id'], 'name': 'doc', 'url': '',
            'description': 'doc', 'format': 'pdf'
        }
        updated = call_action('resource_update', context, **data_to_update)
        assert updated['resource_type'] == 'regular-resource'

    def test_resource_dummy_validator_for_resource_only(self):
        context = _create_context(self.sysadmin)
        context.update(is_doc=True)
        resources = [
            {'name': 'doc', 'description': 'doc', 'format': 'pdf'}
        ]
        data_dict = _create_dataset_dict('test-dataset-4', self.orgname, resources=resources)
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-4')
        assert dataset.get('resources')[0]['url'] == '', dataset.get('resources')[0]['url']

    def test_resource_dummy_validator_for_doc_only(self):
        context = _create_context(self.sysadmin)
        resources = [
            {'name': 'doc', 'format': 'pdf', 'url': ''}
        ]
        data_dict = _create_dataset_dict('test-dataset-4', self.orgname, resources=resources)
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-4')
        assert dataset.get('resources')[0]['description'] == ''

    def test_resource_dummy_validator_for_remains_as_is_on_update(self):
        context = _create_context(self.sysadmin)
        res_meta = {'name': 'regular-resource', 'format': 'csv', 'url': '', 'description': 'Very Good Description'}
        resources = [res_meta]
        data_dict = _create_dataset_dict('test-dataset-4', self.orgname, resources=resources)
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-4')
        res_meta.update({'id': dataset['resources'][0]['id'], 'url': 'https://ckan.io'})
        call_action('resource_update', context, **res_meta)
        res = call_action('resource_show', context, id=res_meta['id'])
        assert res['description'] == 'Very Good Description'
        assert res['url'] == 'https://ckan.io'

    def teardown(slef):
        reset_db()


class TestValidators(FunctionalTestBase):
    def test_dataset_by_sysadmin_and_admin_is_not_approval_pending(self):
        core_factories.User(name='george')
        core_factories.Organization(
            users=[{'name': 'george', 'capacity': 'admin'}],
            name='us-ed-1',
            id='us-ed-1'
        )

        sysadmin = core_factories.Sysadmin()
        context = _create_context(sysadmin)
        data_dict = _create_dataset_dict('test-dataset-1', 'us-ed-1')
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-1')
        assert_equals(dataset.get('approval_state'), 'active')

        context = _create_context({'name': 'george'})
        data_dict = _create_dataset_dict('test-dataset-2', 'us-ed-1')
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-2')
        assert_equals(dataset.get('approval_state'), 'active')


    def test_dataset_by_editor_is_approval_pending(self):
        core_factories.User(name='john')
        core_factories.Organization(
            users=[{'name': 'john', 'capacity': 'editor'}],
            name='us-ed-2',
            id='us-ed-2'
        )

        context = _create_context({'name': 'john'})
        data_dict = _create_dataset_dict('test-dataset', 'us-ed-2')
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset')
        assert_equals(dataset['approval_state'], 'approval_pending')


    def test_dataset_update_by_editor_remains_rejected(self):
        core_factories.User(name='george')
        core_factories.User(name='john')
        core_factories.Organization(
            users=[
                {'name': 'george', 'capacity': 'admin'},
                {'name': 'john', 'capacity': 'editor'}
            ],
            name='us-ed-3',
            id='us-ed-3'
        )

        context_editor = _create_context({'name': 'john'})
        data_dict = _create_dataset_dict('test-dataset', 'us-ed-3')
        package = call_action('package_create', context_editor, **data_dict)
        context_admin = _create_context({'name': 'george'})
        call_action(
            'package_patch',
            context_admin,
            **{'approval_state': 'rejected', 'id': package['id']}
        )
        data_dict['id'] = package['id']
        call_action('package_update', context_editor, **data_dict)
        dataset = call_action('package_show', context_editor, id='test-dataset')
        assert_equals(dataset['approval_state'], 'rejected')


    def test_dataset_update_by_editor_remains_approved(self):
        core_factories.User(name='george')
        core_factories.User(name='john')
        core_factories.Organization(
            users=[
                {'name': 'george', 'capacity': 'admin'},
                {'name': 'john', 'capacity': 'editor'}
            ],
            name='us-ed-4',
            id='us-ed-4'
        )

        context_editor = _create_context({'name': 'john'})
        data_dict = _create_dataset_dict('test-dataset', 'us-ed-4')
        package = call_action('package_create', context_editor, **data_dict)
        context_admin = _create_context({'name': 'george'})
        call_action(
            'package_patch',
            context_admin,
            **{'approval_state': 'approved', 'id': package['id']}
        )
        data_dict['id'] = package['id']
        call_action('package_update', context_editor, **data_dict)
        dataset = call_action('package_show', context_editor, id='test-dataset')
        assert_equals(dataset['approval_state'], 'approved')


def _create_context(user):
    return {'model': model, 'user': user['name']}


def _create_dataset_dict(package_name, office_name='us-ed', resources=[]):
    return {
        'name': package_name,
        'resources': resources,
        'contact_name': 'Stu Shepard',
        'program_code': '321',
        'access_level': 'public',
        'bureau_code': '123',
        'contact_email': '%s@email.com' % package_name,
        'notes': 'notes',
        'owner_org': office_name,
        'title': 'Title',
        'identifier': 'identifier'
    }
