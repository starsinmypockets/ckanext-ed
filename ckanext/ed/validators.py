import logging
import re

from ckan.plugins import toolkit
import ckan.lib.navl.dictization_functions as df

Invalid = df.Invalid
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


#pattern from https://html.spec.whatwg.org/#e-mail-state-(type=email)
email_pattern = re.compile(r"^(?!\.)(?!.*\.$)(?!.*?\.\.)"\
                            "[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"\
                            "(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"\
                            "(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")

def email_validator(value):
    if value:
        try:
            if not email_pattern.match(value):
                raise Invalid('Please enter a valid email address.')
        except TypeError:
            raise Invalid('Please enter a valid email address.')
    return value


