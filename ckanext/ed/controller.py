import os
import logging

from ckan import model
from ckan.common import g, response
from ckan.lib import base
from ckan.plugins import toolkit
from ckan.views.user import _extra_template_variables

from ckanext.ed.helpers import get_storage_path_for
from ckanext.ed.mailer import mail_package_publish_update_to_user

log = logging.getLogger(__name__)


class PendingRequestsController(base.BaseController):
    def list_requests(self):
        user_orgs = toolkit.get_action(
            'organization_list_for_user'
        )({'user': toolkit.c.user}, {'user': toolkit.c.user})
        admin_org_id = [
            'owner_org:' + i['id'] for i in user_orgs
            if i.get('capacity') == 'admin'
        ]
        admin_fq_string = ''
        if len(admin_org_id):
            admin_fq_string = 'AND (%s)' % ' OR '.join(admin_org_id)
        pending_dataset = toolkit.get_action('package_search')(
            data_dict={
                'fq': 'approval_state:approval_pending %s' % admin_fq_string,
                'include_private': True,
                'extras': {'from_dashboard': True},
            })['results']

        # filter datasets that are not under admins organisation
        context = {
            u'for_view': True, u'user': g.user, u'auth_user_obj': g.userobj}
        data_dict = {u'user_obj': g.userobj, u'include_datasets': True}
        extra_vars = _extra_template_variables(context, data_dict)
        if extra_vars is None:
            raise toolkit.NotAuthorized
        extra_vars['pending_dataset'] = pending_dataset
        return base.render(u'user/dashboard_requests.html', extra_vars)


class DownloadController(base.BaseController):
    def download_zip(self, zip_id):
        if not zip_id:
            toolkit.abort(404, toolkit._('Resource data not found'))
        file_name, package_name = zip_id.split('::')
        file_path = get_storage_path_for('temp-ed/' + file_name)

        if not os.path.isfile(file_path):
            toolkit.abort(404, toolkit._('Resource data not found'))

        if not package_name:
            package_name = 'resources'
        package_name += '.zip'

        with open(file_path, 'r') as f:
            response.write(f.read())

        response.headers['Content-Type'] = 'application/octet-stream'
        response.content_disposition = 'attachment; filename=' + package_name
        os.remove(file_path)


class ApproveRejectController(base.BaseController):
    def approve(self, id):
        _make_action(id, 'approve')

    def reject(self, id):
        feedback = toolkit.request.params.get(
            'feedback', 'No feedback provided')
        _make_action(id, 'reject', feedback=feedback)


def _raise_not_authz_or_not_pending(id):
    toolkit.check_access(
        'package_delete', {'model': model, 'user': toolkit.c.user}, {'id': id})
    # check approval_state is pending
    data_dict = toolkit.get_action('package_show')({}, {'id': id})
    if data_dict.get('approval_state') != 'approval_pending':
        raise toolkit.ObjectNotFound('Dataset "{}" not found'.format(id))


def _make_action(package_id, action='reject', feedback=None):
    states = {
        'reject': 'rejected',
        'approve': 'approved'
    }
    # check access and state
    _raise_not_authz_or_not_pending(package_id)
    data_dict = toolkit.get_action('package_patch')(
        {'model': model, 'user': toolkit.c.user},
        {'id': package_id, 'approval_state': states[action]}
    )
    msg = 'Dataset "{0}" {1}'.format(data_dict['title'], states[action])
    if action == 'approve':
        mail_package_publish_update_to_user({}, data_dict, event='approval')
        toolkit.h.flash_success(msg)
    else:
        mail_package_publish_update_to_user(
            {}, data_dict, event='rejection', feedback=feedback)
        toolkit.h.flash_error(msg)
    toolkit.redirect_to(
        controller='package', action='read', id=data_dict['name'])
