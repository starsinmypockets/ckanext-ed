import logging

from ckan import model
from ckan.common import config
from ckan.plugins import toolkit
from ckan.lib.mailer import mail_user
from ckan.lib.base import render_jinja2
from ckan.logic.action.get import member_list as core_member_list

log = logging.getLogger(__name__)


def mail_package_publish_request_to_admins(
                        context, data_dict, event='approval', feedback=None):
    members = core_member_list(
        context=context,
        data_dict={'id': data_dict.get('owner_org')}
    )
    admin_ids = [i[0] for i in members if i[2] == 'Admin']
    for admin_id in admin_ids:
        user = model.User.get(admin_id)
        if user.email:
            subj = _compose_email_subj(data_dict, event='request')
            body = _compose_email_body(data_dict, user, event='request')
            header = {'Content-Type': 'text/html; charset=UTF-8'}
            mail_user(user, subj, body, headers=header)
            log.debug('[email] Pakcage publishing request email sent to {0}'.format(user.name))


def mail_package_publish_update_to_user(
                            context, pkg_dict, event='approval', feedback=None):
    context.setdefault('model', model)
    user = model.User.get(pkg_dict['creator_user_id'])
    if user and user.email:
        subj = _compose_email_subj(pkg_dict, event=event)
        body = _compose_email_body(pkg_dict, user, event=event, feedback=feedback)
        header = {'Content-Type': 'text/html; charset=UTF-8'}
        mail_user(user, subj, body, headers=header)
        log.debug('[email] Data container update email sent to {0}'.format(user.name))


def _compose_email_subj(data_dict, event='request'):
    return '[US ED] Package Publishing {0}: {1}'.format(event.capitalize(), data_dict.get('title'))


def _compose_email_body(data_dict, user, event='request', feedback=None):
    pkg_link = toolkit.url_for('dataset_read', id=data_dict['name'], qualified=True)
    return render_jinja2('emails/package_publish_{0}.html'.format(event), {
        'admin_name': user.fullname or user.name,
        'site_title': config.get('ckan.site_title'),
        'site_url': config.get('ckan.site_url'),
        'package_title': data_dict.get('title'),
        'package_description': data_dict.get('notes', ''),
        'package_url': pkg_link,
        'publisher_name': data_dict.get('contact_name'),
        'feedback': feedback
    })
