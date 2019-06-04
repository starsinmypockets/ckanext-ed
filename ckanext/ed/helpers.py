from datetime import datetime
import json
import inspect
import logging
import os

from ckan.common import config, is_flask_request, c, request
from ckan.plugins import toolkit


log = logging.getLogger()

def _get_action(action, context_dict, data_dict):
    return toolkit.get_action(action)(context_dict, data_dict)


def get_groups():
    # Helper used on the homepage for showing groups

    data_dict = {
        'all_fields': True
    }
    groups = _get_action('group_list', {}, data_dict)

    return groups


def get_recently_updated_datasets(limit=5):
    '''
     Returns recent created or updated datasets.
    :param limit: Limit of the datasets to be returned. Default is 5.
    :type limit: integer
    :param user: user name
    :type user: string

    :returns: a list of recently created or updated datasets
    :rtype: list
    '''
    try:
        pkg_search_results = toolkit.get_action('package_search')(
            data_dict={
                'sort': 'metadata_modified desc',
                'rows': limit
            })['results']
        return pkg_search_results

    except toolkit.ValidationError, search.SearchError:
        return []
    else:
        log.warning('Unexpected Error occured while searching')
        return []

def get_most_popular_datasets(limit=5):
    '''
     Returns most popular datasets based on total views.
    :param limit: Limit of the datasets to be returned. Default is 5.
    :type limit: integer
    :param user: user name
    :type user: string

    :returns: a list of most popular datasets
    :rtype: list
    '''
    data = pkg_search_results = toolkit.get_action('package_search')(
        data_dict={
            'sort': 'views_total desc',
            'rows': limit,
        })['results']

    return data


def get_storage_path_for(dirname):
    """Returns the full path for the specified directory name within
    CKAN's storage path. If the target directory does not exists, it
    gets created.

    :param dirname: the directory name
    :type dirname: string

    :returns: a full path for the specified directory name within CKAN's storage path
    :rtype: string
    """
    storage_path = config.get('ckan.storage_path')
    target_path = os.path.join(storage_path, 'storage', dirname)
    if not os.path.exists(target_path):
        try:
            os.makedirs(target_path)
        except OSError, exc:
            log.error('Storage directory creation failed. Error: %s' % exc)
            target_path = os.path.join(storage_path, 'storage')
            if not os.path.exists(target_path):
                log.info('CKAN storage directory not found also')
                raise

    return target_path


def get_total_views_for_dataset(id):
    data_dict = {
        'id': id,
        'include_tracking': True
    }

    try:
        dataset = _get_action('package_show', {}, data_dict)
        return dataset.get('tracking_summary').get('total')
    except Exception:
        return 0


def is_admin(user, office=None):
    """
    Returns True if user is admin of given organisation.
    If office param is not provided checks if user is admin of any organisation

    :param user: user name
    :type user: string
    :param office: office id
    :type office: string

    :returns: True/False
    :rtype: boolean
    """
    user_orgs = _get_action(
                'organization_list_for_user', {'user': user}, {'user': user})
    if office is not None:
        return any([i.get('capacity') == 'admin' \
                and i.get('id') == office for i in user_orgs])
    return any([i.get('capacity') == 'admin' for i in user_orgs])


def get_pending_datasets(user, include_rejected=False):
    """
    Returns List of datasets requested for approval.
    Includes rejecred datasets if include_rejected is set to True.

    :param user: username
    :type user: string
    :include_rejected: Flag to include rejecte datasets or not
    :type include_rejected: boolean

    :returns: List of matching datasets
    :rtype: list
    """
    role = 'editor' if include_rejected else 'admin'
    user_orgs = _get_action(
        'organization_list_for_user', {'id': user}, {'id': user})
    user_org_pemrs = [
        'owner_org:' + i['id'] for i in user_orgs if i.get('capacity') == role
    ]
    fq_string = '(approval_state:approval_pending{0}){1}{2}'.format(
        # Include rejected datasets if needed
        ' OR approval_state:rejected' if include_rejected else '',
        # Filter datasets by orgs user is admin of
        ' AND (%s)' % ' OR '.join(user_org_pemrs) if len(user_org_pemrs) else '',
        # Filter datasets not belonging to ediotr
        ' AND creator_user_id:%s' % (user) if include_rejected else ''
    )
    pending_dataset = toolkit.get_action('package_search')(
        data_dict={
            'fq': fq_string,
            'include_private': True,
            'extras': {'from_dashboard': True},
        })['results']
    return pending_dataset


def workflow_activity_create(
                    activity, dataset_id, dataset_name, user, feedback=None):
    activity_context = {'ignore_auth': True}
    data_dict = {
        'user_id': user,
        'object_id': dataset_id,
        'activity_type': 'changed package',
        'data': {
            'workflow_activity': activity,
            'package': {'name': dataset_name, 'id': dataset_id},
            'feedback': feedback
        }
    }
    toolkit.get_action('activity_create')(activity_context, data_dict)


def custom_activity_renderer(context, activity):
    if 'workflow_activity' not in activity.get('data', {}):
        # Default core one
        return toolkit._("{actor} updated the dataset {dataset}")

    activity_name = activity['data']['workflow_activity']

    if activity_name == 'submitted_for_review':
        return toolkit._("{actor} requested a review for new dataset {dataset}")
    elif activity_name == 'resubmitted_for_review':
        return toolkit._("{actor} made changes and requested a review for dataset {dataset}")
    elif activity_name == 'dataset_approved':
        return toolkit._("{actor} approved dataset {dataset} for publication")
    elif activity_name == 'dataset_rejected':
        if activity['data'].get('feedback'):
            return toolkit._(
                "{actor} rejected dataset {dataset} for publication " +
                "with the following feedback: %s" % activity['data']['feedback'])
        else:
            return toolkit._("{actor} rejected dataset {dataset} for publication")

    return toolkit._("{actor} updated the dataset {dataset}")


def get_latest_rejection_feedback(pkg_id):
    context = {'ignore_auth': True}
    data_dict = {
        'id': pkg_id,
        'get_workflow_activities': True
    }

    activities = toolkit.get_action('package_activity_list')(
        context, data_dict)

    for activity in activities:
        if (activity['data']['workflow_activity'] == 'dataset_rejected' and
                activity['data'].get('feedback')):
            return activity['data']['feedback']

def quality_mark(package):
    """
    :param pacakge:
        Package dictionary
    :return: dict
         ['machine'] - True if there's at least one machine readable resource.
         ['doc'] - True if there's at least one document resource.
    """
    at_least_one_machine_resource = \
        any([True for r in package['resources'] if r['format']=='CSV' or
                                            r['format'] == 'XML' or
                                            r['mimetype'] == 'text/csv' or
                                            r['mimetype'] == 'text/json' or
                                            r['mimetype'] == 'application/json' or
                                            r['url_type']!='upload' and r['url']!=''])



    at_least_one_document_resource = \
        any([True for r in package['resources'] if r.get('resource_type')=='doc'])

    return { 'machine' : at_least_one_machine_resource,
             'doc' : at_least_one_document_resource }

def get_org_for_package(package):
    """

    :param package:
    :return: organization name
    """
    return (
        package['organization']['title']
    )


def load_meta_file(file_path):
    """
    Given a path like "ckanext.ed.schemas:choices.json"
    find the second part relative to the import path of the first
    """
    module_name, file_name = file_path.split(':', 1)
    module = __import__(module_name, fromlist=[''])
    file_path = os.path.join(os.path.dirname(inspect.getfile(module)),
                             file_name)
    return open(file_path)


def load_choices(field_meta=None):
    fn = load_meta_file(field_meta.get('choices_file_path'))
    json_data = json.load(fn)
    return json_data


def alphabetize_dict(items, sort_by='display_name'):
    sorted_dict = sorted(items, key=lambda x: x[sort_by])
    return sorted_dict

def get_any(list_, key=None):
    if key is not None:
        return any(i[key] for i in list_)
    return any(list_)
