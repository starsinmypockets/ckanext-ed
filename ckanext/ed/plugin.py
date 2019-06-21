from ckan.lib.activity_streams import activity_stream_string_functions
from ckan.lib.plugins import DefaultTranslation
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.ed import actions, helpers, validators


class EDPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IFacets, inherit=True)

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'ed_get_groups': helpers.get_groups,
            'ed_is_admin': helpers.is_admin,
            'ed_get_recently_updated_datasets': helpers.get_recently_updated_datasets,
            'ed_get_most_popular_datasets': helpers.get_most_popular_datasets,
            'ed_get_total_views_for_dataset': helpers.get_total_views_for_dataset,
            'ed_get_pending_datasets': helpers.get_pending_datasets,
            'ed_get_latest_rejection_feedback': helpers.get_latest_rejection_feedback,
            'quality_mark' : helpers.quality_mark,
            'get_org_for_package' : helpers.get_org_for_package,
            'load_choices': helpers.load_choices,
            'alphabetize_dict' : helpers.alphabetize_dict,
            'get_any': helpers.get_any
        }

    # IActions
    def get_actions(self):
        return {
            'ed_prepare_zip_resources': actions.prepare_zip_resources,
            'package_show': actions.package_show,
            'package_create': actions.package_create,
            'package_update': actions.package_update,
            'package_activity_list': actions.package_activity_list,
            'dashboard_activity_list': actions.dashboard_activity_list,
            'group_activity_list': actions.group_activity_list,
            'recently_changed_packages_activity_list': actions.recently_changed_packages_activity_list
        }

    # IPackageController
    def before_search(self, search_params):
        # For requests dashboard we need approval_pending datasets. Passing in
        # extras that request is sent from dashboard. Return params as is if so
        if search_params.get('extras', {}).get('from_dashboard'):
            return search_params

        search_params.update({
            'fq': '!(approval_state:approval_pending OR approval_state:rejected) ' + search_params.get('fq', '')
        })
        return search_params

    # IConfigurer
    def update_config(self, config_):


        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ed')

        activity_stream_string_functions['changed package'] = helpers.custom_activity_renderer


    # IRoutes
    def before_map(self, map):
        publish_controller = 'ckanext.ed.controller:StateUpdateController'
        map.connect('dataset.workflow', '/dataset/workflow/{id}',
                    controller='ckanext.ed.controller:WorkflowActivityStreamController',
                    action='list_activities')
        map.connect('dashboard.requests', '/dashboard/requests',
                    controller='ckanext.ed.controller:PendingRequestsController',
                    action='list_requests')
        map.connect('/dataset-publish/{id}/approve',
                    controller=publish_controller,
                    action='approve')
        map.connect('/dataset-publish/{id}/reject',
                    controller=publish_controller,
                    action='reject')
        map.connect('/dataset-publish/{id}/resubmit',
                    controller=publish_controller,
                    action='resubmit')
        map.connect(
            'download_zip',
            '/download/zip/{zip_id}',
            controller='ckanext.ed.controller:DownloadController',
            action='download_zip'
        )

        map.connect('help_url',
                    '/help',
                    controller='ckanext.ed.controller:HelpController',
                    action="external_help")

        map.connect('/user/logged_in',
                    controller='ckanext.ed.controller:CustomeUserController',
                    action="logged_in")

        ## Docs
        map.connect('/dataset/new_resource/{id}',
                    controller='ckanext.ed.controller:NewResourceController',
                    action='new_resource')
        map.connect('doc',
                    '/dataset/new_doc/{id}',
                    controller='ckanext.ed.controller:NewResourceController',
                    action='new_doc')

        map.connect('dataset.docs', '/dataset/docs/{id}',
                    controller='ckanext.ed.controller:DocumentationController',
                    action='read_doc')

        map.connect('/dataset/docs/{dataset_id}/pin/{resource_id}',
                    controller='ckanext.ed.controller:DocumentationController',
                    action='pin')

        map.connect('/dataset/docs/{dataset_id}/unpin/{resource_id}',
                    controller='ckanext.ed.controller:DocumentationController',
                    action='unpin')

        map.connect('dataset.disqus', '/dataset/{id}/disqus',
                    controller='ckanext.ed.controller:DisqusController',
                    action='read_disqus')

        ## package
        map.connect('dataset.new','/dataset/new',
                    controller='ckan.controllers.package:PackageController',
                    action='new')
        map.connect('/dataset/{id}',
                    controller='ckanext.ed.controller:EdPackageController',
                    action='read')
        return map

    # IValidators
    def get_validators(self):
        return {
            'state_validator': validators.state_validator,
            'resource_type_validator': validators.resource_type_validator,
            'dummy_validator': validators.dummy_validator,
            'package_name_validator': validators.package_name_validator
        }

    def dataset_facets(self, facets_dict, package_type):
        from collections import OrderedDict
        facets_dict = OrderedDict({})
        facets_dict['groups'] = "Major Topics"
        facets_dict['tags'] = "Tags"
        facets_dict['organization'] = "Publishers"
        facets_dict['res_format'] = "Formats"
        facets_dict['spatial'] = "Geography"
        facets_dict['license_id'] = "License"
        facets_dict['level_of_data_string'] = "Level Of Data"
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        facets_dict['organization'] = 'Publishers'

