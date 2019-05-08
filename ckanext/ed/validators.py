import logging

import logic
from ckan.plugins import toolkit

log = logging.getLogger(__name__)


def state_validator(key, data, errors, context):
    user_orgs = toolkit.get_action('organization_list_for_user')(
        context, {'id': context['user']})
    office_id = data.get(('owner_org',))
    state = data.pop(key, None)

    # It's hard to to tell on which action validator is executed exectly, execpt
    # If context does not include package -> action=package_create
    # If context includes package and state is not None -> action=package_patch
    # If context includes package and state in not None -> action=package_update
    if context.get('package') and not state:
        state = context.get('package').extras.get('approval_state')

    # If the user is member of the organization but not admin, keep state as is
    for org in user_orgs:
        if org.get('id') == office_id:
            if org.get('capacity') == 'admin':
                # If no state provided and user is an admin, default to active
                state = state or 'active'
            else:
                # If not admin, create as pending or keep state as was
                state = state or 'approval_pending'
    data[key] = state


def dummy_validator(key, data, errors, context):
    '''inserts dummy values (empty string) into required fields according to resource type.
    Eg if we are filling documentation resource, required fields for regular
    resouces will be filled with empty string and vice-versa.
    '''
    is_doc = context.get('is_doc')
    schema = toolkit.h.scheming_get_dataset_schema('dataset')
    resource_schema = schema['resource_fields']
    field_name = key[-1]
    field_schema = list(filter(
                    lambda x: x['field_name'] == field_name, resource_schema))[0]
    if field_schema.get('required'):
        if is_doc and (field_schema.get('resource_type') == 'resource_only'):
            data[key] = ''
        elif not is_doc and (field_schema.get('resource_type') == 'doc_only'):
            data[key] = ''


def resource_type_validator(key, data, errors, context):
    if data[key]:
        return
    resource_info = {}
    try:
        # When updating resource hidden fields are still gettin empty values
        # We need to check if resource already exists and if so check it's resource_type
        resource_id = data[(u'resources', key[1], u'id')]
        resource_info = logic.get_action('resource_show')(
            {'user': context['user']},
            {'id': resource_id, 'resource_id': resource_id}
        )
    except KeyError:
        pass
    is_doc = context.get('is_doc') or resource_info.get('resource_type') == 'doc'
    data[key] = 'doc' if is_doc else 'regular-resource'
