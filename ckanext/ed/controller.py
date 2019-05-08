import os
import logging
import cgi


from ckan.common import g, _, response, request, c, config
import ckan.lib.helpers as h
from paste.deploy.converters import asbool

from ckan import model
from ckan.lib import base
from ckan.lib.plugins import lookup_package_plugin
import logic
import ckan
from ckan.logic import NotFound
from ckan.plugins import toolkit
from ckan.views.user import _extra_template_variables
import ckan.lib.navl.dictization_functions as dict_fns


from ckanext.ed.helpers import get_storage_path_for, get_pending_datasets, is_admin, workflow_activity_create
from ckanext.ed.mailer import mail_package_publish_update_to_user, mail_package_publish_request_to_admins
from ckan.controllers.package import PackageController
from ckan.controllers.user import UserController
import ckan.plugins as p


from ckan.common import config
from paste.deploy.converters import asbool

import ckan.lib.navl.dictization_functions as dictization_functions

log = logging.getLogger(__name__)


abort = base.abort
render = base.render

check_access = logic.check_access
get_action = logic.get_action
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
UsernamePasswordError = logic.UsernamePasswordError

DataError = dictization_functions.DataError
unflatten = dictization_functions.unflatten




abort = base.abort

get_action = logic.get_action
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
clean_dict = logic.clean_dict
tuplize_dict = logic.tuplize_dict
parse_params = logic.parse_params


class DocumentationController(PackageController):
    def read_doc(self, id):
        edit = request.params.get('edit')
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'for_view': True,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id, 'include_tracking': True}
        if edit:
            try:
                toolkit.check_access('package_update', context, data_dict)
            except NotFound:
                abort(404, _('Dataset not found'))
            except NotAuthorized:
                abort(403, _('User %r not authorized to edit %s') % (c.user, id))
        # check if package exists
        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            c.pkg = context['package']
        except (NotFound, NotAuthorized):
            abort(404, _('Dataset not found'))

        package_type = c.pkg_dict['type'] or 'dataset'
        self._setup_template_variables(context, {'id': id},
                                       package_type=package_type)

        return toolkit.render('package/documentations.html',
                      extra_vars={'dataset_type': package_type, 'edit': edit})

    def pin(self, dataset_id, resource_id):
        self._update_pin(dataset_id, resource_id, pin=True)

    def unpin(self, dataset_id, resource_id):
        self._update_pin(dataset_id, resource_id, pin=False)

    def _update_pin(self, dataset_id, resource_id, pin=False):
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}
        toolkit.check_access(
            'resource_update', context, {"package_id": dataset_id})
        pkg_dict = get_action('package_show')(context, {'id': dataset_id})
        for res in pkg_dict['resources']:
            if pin:
                res['pinned'] = res['id'] == resource_id
            else:
                if res['id'] == resource_id:
                    res['pinned'] = False
                    break
        get_action('package_patch')(context, pkg_dict)
        if pin:
            get_action('package_resource_reorder')(
                        context, {'id': dataset_id, 'order': [resource_id]})
        h.redirect_to(
            controller='ckanext.ed.controller:DocumentationController',
            action='read_doc',
            id=dataset_id
        )

    def _is_true(self, value):
        if value == 'True' or value == 'true':
            return True
        if value == 'False' or value == 'false':
            return False
        return bool(value)


class NewResourceController(base.BaseController):
    def new_resource(self, id, data=None, errors=None, error_summary=None):
        save_action = request.params.get('save')
        is_doc = 'from-doc' in save_action if save_action else False
        return self._new_resource(id, data=data, errors=errors, error_summary=error_summary, is_doc=is_doc)

    def new_doc(self, id, data=None, errors=None, error_summary=None, is_doc=True):
        return self._new_resource(id, data=data, errors=errors, error_summary=error_summary, is_doc=True)

    def _new_resource(self, id, data=None, errors=None, error_summary=None, is_doc=False):
        ''' FIXME: This is a temporary action to allow styling of the
        forms. '''
        if request.method == 'POST' and not data:
            save_action = request.params.get('save')
            data = data or \
                clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(
                                                           request.POST))))
            # we don't want to include save as it is part of the form
            del data['save']
            resource_id = data['id']
            del data['id']

            context = {
                'model': model,
                'session': model.Session,
                'user': c.user,
                'auth_user_obj': c.userobj,
                'is_doc': is_doc
            }

            # see if we have any data that we are trying to save
            data_provided = False
            for key, value in data.iteritems():
                if ((value or isinstance(value, cgi.FieldStorage))
                        and key != 'resource_type'):
                    data_provided = True
                    break

            if not data_provided and "go-dataset-complete" not in save_action:
                if save_action == 'go-dataset':
                    # go to final stage of adddataset
                    h.redirect_to(controller='package', action='edit', id=id)
                # see if we have added any resources
                try:
                    data_dict = get_action('package_show')(context, {'id': id})
                except NotAuthorized:
                    abort(403, _('Unauthorized to update dataset'))
                except NotFound:
                    abort(404, _('The dataset {id} could not be found.'
                                 ).format(id=id))
                require_resources = asbool(
                    config.get('ckan.dataset.create_on_ui_requires_resources',
                               'True')
                )
                if require_resources and not len(data_dict['resources']):
                    # no data and configured to require resource: stay on page
                    msg = _('You must add at least one data resource')
                    # On new templates do not use flash message

                    if asbool(config.get('ckan.legacy_templates')):
                        h.flash_error(msg)
                        h.redirect_to(controller='package',
                                      action='new_resource', id=id)
                    else:
                        errors = {}
                        error_summary = {_('Error'): msg}
                        return self.new_resource(id, data, errors,
                                                 error_summary)
                # XXX race condition if another user edits/deletes
                data_dict = get_action('package_show')(context, {'id': id})
                get_action('package_update')(
                    dict(context, allow_state_change=True),
                    dict(data_dict, state='active'))
                h.redirect_to(controller='package', action='read', id=id)

            data['package_id'] = id
            try:
                if resource_id:
                    data['id'] = resource_id
                    get_action('resource_update')(context, data)
                else:
                    get_action('resource_create')(context, data)
            except ValidationError as e:
                errors = e.error_dict
                error_summary = e.error_summary
                return self.new_resource(id, data, errors, error_summary)
            except NotAuthorized:
                abort(403, _('Unauthorized to create a resource'))
            except NotFound:
                abort(404, _('The dataset {id} could not be found.'
                             ).format(id=id))
            if save_action == 'go-metadata-from-doc':
                # XXX race condition if another user edits/deletes
                data_dict = get_action('package_show')(context, {'id': id})
                get_action('package_update')(
                    dict(context, allow_state_change=True),
                    dict(data_dict, state='active'))
                h.redirect_to(controller='package', action='read', id=id)
            elif save_action == 'go-dataset':
                # go to first stage of add dataset
                h.redirect_to(controller='package', action='edit', id=id)
            elif 'go-dataset-complete' in save_action:
                # go to first stage of add dataset
                h.redirect_to(controller='package', action='read', id=id)
            elif save_action == 'docs' or save_action == 'doc-again-from-doc':
                h.redirect_to('/dataset/new_doc/{id}'.format(id=id))
            else:
                # add more resources
                h.redirect_to(controller='package', action='new_resource',
                              id=id)

        # get resources for sidebar
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj, 'is_doc': is_doc}
        try:
            pkg_dict = get_action('package_show')(context, {'id': id})
        except NotFound:
            abort(404, _('The dataset {id} could not be found.').format(id=id))
        try:
            toolkit.check_access(
                'resource_create', context, {"package_id": pkg_dict["id"]})
        except NotAuthorized:
            abort(403, _('Unauthorized to create a resource for this package'))

        package_type = pkg_dict['type'] or 'dataset'

        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary, 'action': 'new',
                'resource_form_snippet': self._resource_form(package_type),
                'dataset_type': package_type}
        vars['pkg_name'] = id
        vars['is_doc'] = is_doc
        # required for nav menu
        # logging.error(pkg_dict)
        vars['pkg_dict'] = pkg_dict
        template = 'package/new_resource_not_draft.html'
        if pkg_dict['state'].startswith('draft'):
            vars['stage'] = ['complete', 'active']
            if is_doc:
                vars['stage'] = ['complete', 'complete', 'active']
            template = 'package/new_resource.html'
        return toolkit.render_snippet(template, data=vars)

    def _resource_form(self, package_type):
        # backwards compatibility with plugins not inheriting from
        # DefaultDatasetPlugin and not implmenting resource_form
        plugin = lookup_package_plugin(package_type)
        if hasattr(plugin, 'resource_form'):
            result = plugin.resource_form()
            if result is not None:
                return result
        return lookup_package_plugin().resource_form()


class WorkflowActivityStreamController(base.BaseController):
    def list_activities(self, id):
        '''Render package's workflow activity stream page.'''

        context = {
            'model': model, 'session': model.Session, 'user': toolkit.c.user,
            'for_view': True,'auth_user_obj': toolkit.c.userobj
        }
        data_dict = {'id': id}
        try:
            toolkit.check_access('package_update', context, data_dict)
            toolkit.c.pkg_dict = toolkit.get_action('package_show')(context, data_dict)
            toolkit.c.pkg = context['package']
            toolkit.c.package_activity_stream = toolkit.get_action(
                'package_activity_list_html')(
                context, {
                    'id': toolkit.c.pkg_dict['id'],
                    'get_workflow_activities': True
                })
            dataset_type = toolkit.c.pkg_dict['type'] or 'dataset'
        except NotFound:
            base.abort(404, _('Dataset not found'))
        except toolkit.NotAuthorized:
            base.abort(403, _('Unauthorized to read dataset %s') % id)

        return base.render('package/activity.html', {'dataset_type': dataset_type})


class PendingRequestsController(base.BaseController):
    def list_requests(self):
        if not toolkit.c.userobj:
            base.abort(403, _('Not authorized to see this page'))
        is_editor = not is_admin(toolkit.c.user)
        pending_dataset = get_pending_datasets(toolkit.c.userobj.id, is_editor)
        context = {
            u'for_view': True, u'user': g.user, u'auth_user_obj': g.userobj}
        data_dict = {u'user_obj': g.userobj, u'include_datasets': True}
        extra_vars = _extra_template_variables(context, data_dict)
        extra_vars['pending_dataset'] = pending_dataset
        return base.render(u'user/dashboard_requests.html', extra_vars)


class DownloadController(base.BaseController):
    def download_zip(self, zip_id):
        if not zip_id:
            toolkit.abort(404, toolkit._('Data not found'))
        file_name, package_name = zip_id.split('::')
        file_path = get_storage_path_for('temp-ed/' + file_name)

        if not os.path.isfile(file_path):
            toolkit.abort(404, toolkit._('Data not found'))

        if not package_name:
            package_name = 'resources'
        package_name += '.zip'

        with open(file_path, 'r') as f:
            response.write(f.read())

        response.headers['Content-Type'] = 'application/octet-stream'
        response.content_disposition = 'attachment; filename=' + package_name
        os.remove(file_path)


class StateUpdateController(base.BaseController):
    def approve(self, id):
        make_public = toolkit.request.params.get(
            'make_public') == 'true'

        _make_action(id, 'approve', make_public=make_public)

    def reject(self, id):
        feedback = toolkit.request.params.get(
            'feedback', 'No feedback provided')
        _make_action(id, 'reject', feedback=feedback)

    def resubmit(self, id):
        _make_action(id, 'resubmit')


def _raise_not_authz(id, action='reject'):
    if action == 'resubmit':
        toolkit.check_access(
            'package_update', {
                'model': model, 'user': toolkit.c.user}, {'id': id})
    else:
        # Check user is admin of the org pakcage is created for
        try:
            package_dict = toolkit.get_action('package_show')(
                {'model': model, 'user': toolkit.c.user}, {'id': id}
            )
        except toolkit.ObjectNotFound:
            # We don't need ObjectNotFound here
            raise toolkit.NotAuthorized

        is_admin_ = is_admin(toolkit.c.user, package_dict['owner_org'])
        if not is_admin_:
            raise toolkit.NotAuthorized


def _make_action(package_id, action='reject', feedback=None, make_public=None):
    action_props = {
        'reject': {
            'state': 'rejected',
            'message': 'Dataset "{0}" rejected',
            'event': 'rejection',
            'mail_func': mail_package_publish_update_to_user,
            'flash_func': toolkit.h.flash_error,
            'activity': 'dataset_rejected'
        },
        'approve': {
            'state': 'approved',
            'message': ('Dataset "{0}" approved and made public'
                        if make_public else 'Dataset "{0}" approved'),
            'event': 'approval',
            'mail_func': mail_package_publish_update_to_user,
            'flash_func': toolkit.h.flash_success,
            'activity': 'dataset_approved'
        },
        'resubmit': {
            'state': 'approval_pending',
            'message': 'Dataset "{0}" submitted',
            'event': 'request',
            'mail_func': mail_package_publish_request_to_admins,
            'flash_func': toolkit.h.flash_success,
            'activity': 'resubmitted_for_review'
        }
    }
    # check access and state
    _raise_not_authz(package_id, action=action)
    context = {'model': model, 'user': toolkit.c.user}
    patch_data = {
        'id': package_id, 'approval_state': action_props[action]['state']
    }
    if make_public:
        patch_data['private'] = False
    data_dict = toolkit.get_action('package_patch')(context, patch_data)
    action_props[action]['mail_func'](
        context,
        data_dict,
        event=action_props[action]['event'],
        feedback=feedback
    )
    action_props[action]['flash_func'](
        action_props[action]['message'].format(data_dict['title']))
    workflow_activity_create(
        activity=action_props[action]['activity'],
        dataset_id=data_dict['id'],
        dataset_name=data_dict['name'],
        user=toolkit.c.user,
        feedback=feedback
    )
    toolkit.redirect_to(
        controller='package', action='read', id=data_dict['name'])


class HelpController(base.BaseController):
    def external_help(self):
        return toolkit.redirect_to('https://youtube.com')


class CustomeUserController(UserController):
    def me(self, locale=None):
        if not c.user:
            h.redirect_to(locale=locale, controller='user', action='login',
                          id=None)
        user_ref = c.userobj.get_reference_preferred_for_uri()
        # do what seems to be a flask redirect
        h.redirect_to('dashboard.datasets')
