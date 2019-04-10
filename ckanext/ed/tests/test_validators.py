from nose.tools import assert_equals

from ckan import model
from ckan.tests import factories as core_factories
from ckan.tests.helpers import call_action, FunctionalTestBase

import ckan.lib.navl.dictization_functions as df
from  import validators

import nose.tools

from .. import validators


def returns_arg(function):
    '''A decorator that tests that the decorated function returns the argument
    that it is called with, unmodified.

    :param function: the function to decorate
    :type function: function

    Usage:

        @returns_arg
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def call_and_assert(arg, context=None):
        if context is None:
            context = {}
        result = function(arg, context=context)
        assert result == arg, (
            'Should return the argument that was passed to it, unchanged '
            '({arg})'.format(arg=repr(arg)))
        return result
    return call_and_assert


def raises_Invalid(function):
    '''A decorator that asserts that the decorated function raises
    dictization_functions.Invalid.

    Usage:

        @raises_Invalid
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def call_and_assert(*args, **kwargs):
        nose.tools.assert_raises(df.Invalid, function, *args, **kwargs)
    return call_and_assert

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

    def test_email_validator_with_invalid_value(selfs):
        invalid_values = [
            '..test...test..@example.com',
            'test @example.com',
            'test@ example.com',
            'test..test@example.com',
            'test.test...@example.com',
            '...test@example.com',
        ]

        for invalid_value in invalid_values:
            @raises_Invalid
            def call_validator(*args, **kwargs):
                return validators.email_validator(*args, **kwargs)
            call_validator(invalid_value, context={})

    def test_email_validator_with_valid_value(self):
        valid_values = [
            'text@example.com',
            'test.this@example.com',
            'test.this@server.example.com',
        ]

        for valid_value in valid_values:
            @returns_arg
            def call_validator(*args, **kwargs):
                return validators.email_validator(*args, **kwargs)
            call_validator(valid_value)

def _create_context(user):
    return {'model': model, 'user': user['name']}


def _create_dataset_dict(package_name, office_name='us-ed'):
    return {
        'name': package_name,
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
