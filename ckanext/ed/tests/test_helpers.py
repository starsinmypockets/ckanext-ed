from ckan.tests import helpers as test_helpers
from ckan.tests import factories as core_factories

import mock
import ckan
import __builtin__ as builtins

from ckanext.ed import helpers
from ckanext.ed.tests import factories

from pyfakefs import fake_filesystem

from ckan.lib.helpers import url_for


real_open = open
fs = fake_filesystem.FakeFilesystem()
fake_os = fake_filesystem.FakeOsModule(fs)
fake_open = fake_filesystem.FakeFileOpen(fs)

import nose.tools

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises
assert_not_equals = nose.tools.assert_not_equals


def mock_open_if_open_fails(*args, **kwargs):
    try:
        return real_open(*args, **kwargs)
    except (OSError, IOError):
        return fake_open(*args, **kwargs)

class TestHelpers(test_helpers.FunctionalTestBase):
    import cgi

    class FakeFileStorage(cgi.FieldStorage):
        def __init__(self, fp, filename):
            self.file = fp
            self.filename = filename
            self.name = 'upload'

    def test_get_recently_updated_datasets(self):
        user = core_factories.User()
        org = core_factories.Organization(
            users=[{'name': user['name'], 'capacity': 'admin'}]
        )
        factories.Dataset(owner_org=org['id'])
        factories.Dataset(owner_org=org['id'])
        factories.Dataset(owner_org=org['id'])
        dataset = factories.Dataset(owner_org=org['id'])

        result = helpers.get_recently_updated_datasets()
        assert len(result) == 4, 'Epextec 4 but got %s' % len(result)
        assert result[0]['id'] == dataset['id']

        result = helpers.get_recently_updated_datasets(limit=2)
        assert len(result) == 2
        assert result[0]['id'] == dataset['id']

    def test_get_recently_updated_datasets_lists_only_approved(self):
        user = core_factories.User()
        org = core_factories.Organization(
            users=[{'name': user['name'], 'capacity': 'admin'}]
        )
        factories.Dataset(owner_org=org['id'], approval_state='approval_pending')
        factories.Dataset(owner_org=org['id'], approval_state='approval_pending')
        factories.Dataset(owner_org=org['id'])
        dataset = factories.Dataset(owner_org=org['id'])

        result = helpers.get_recently_updated_datasets()
        assert len(result) == 2, 'Epextec 2 but got %s' % len(result)
        assert result[0]['id'] == dataset['id']

    def test_get_groups(self):
        group1 = core_factories.Group()

        result = helpers.get_groups()
        assert len(result) == 1
        core_factories.Group()
        core_factories.Group()
        core_factories.Group()
        result = helpers.get_groups()
        assert result[0]['id'] == group1['id']
        assert len(result) == 4

    def test_is_admin(self):
        core_factories.User(name='george')
        core_factories.User(name='john')
        core_factories.User(name='paul')
        core_factories.Organization(
            users=[
                {'name': 'george', 'capacity': 'admin'},
                {'name': 'john', 'capacity': 'editor'},
                {'name': 'paul', 'capacity': 'reader'}
            ]
        )

        result = helpers.is_admin('george')
        assert result, '%s is not True' % result
        result = helpers.is_admin('john')
        assert not result, '%s is not False' %  result
        result = helpers.is_admin('paul')
        assert not result, '%s is not False' % result
        result = helpers.is_admin('ringo')
        assert not result, '%s is not False' %  result

    @test_helpers.change_config('ckan.storage_path', '/doesnt_exist')
    @mock.patch.object(ckan.lib.uploader, 'os', fake_os)
    @mock.patch.object(builtins, 'open', side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, '_storage_path', new='/doesnt_exist')
    def test_quality_mark(self, mock_open):
        import StringIO
        csv_content = '''
                        Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm, Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, Normal mm
                        SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
                        MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
                        NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
                        '''
        xml_content = '''
                        <?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
                        <note>
                            <to>Tove</to>
                            <from>Jani</from>
                            <heading>Reminder</heading>
                            <body>Don't forget me this weekend!</body>
                        </note>
                        '''
        json_content = '''{ "scheming_version": 1,
                             "dataset_type": "dataset",
                             "about": "Dataset schema for US Dept. of Education",
                             "about_url": "https://www.viderum.com/"
                             }
                             '''

        # test csv file upload
        test_csv_file = StringIO.StringIO()
        test_csv_file.write(csv_content)
        test_csv_resource = TestHelpers.FakeFileStorage(test_csv_file, "test.csv")

        user = core_factories.User()
        org = core_factories.Organization(
            users=[{'name': user['name'], 'capacity': 'admin'}]
        )
        package = factories.Dataset(owner_org=org['id'])
        context = {'user' : user['name']}
        params = {
            'package_id': package['id'],
            'url': 'http://data',
            'name': 'A nice resource',
            'upload': test_csv_resource
        }

        result = test_helpers.call_action('resource_create', context, **params)
        dataset = test_helpers.call_action('package_show', id=package['id'])
        quality_mark = helpers.quality_mark(dataset)
        assert_equals(
            (quality_mark['machine'], quality_mark['doc']), (True, False))


        # now add an xml documentation
        test_doc_file = StringIO.StringIO()
        test_doc_file.write(xml_content)
        test_doc_resource = TestHelpers.FakeFileStorage(test_doc_file, "documentation.xml")

        params = {
            'package_id' : package['id'],
            'name' : 'A document resource',
            'resource_type' : 'doc',
            'upload' : test_doc_resource,
            'description': "Test Documentation",
            'url' : "http://example.com"
        }
        result = test_helpers.call_action('resource_create', context, **params)
        dataset = test_helpers.call_action('package_show', id=package['id'])
        quality_mark = helpers.quality_mark(dataset)
        assert_equals(
           (quality_mark['machine'], quality_mark['doc']), (True, True)
        )

        # now test with no doc and no machine readable
        del package
        package = factories.Dataset(owner_org=org['id'])
        quality_mark = helpers.quality_mark(package)
        assert_equals(
            (quality_mark['machine'], quality_mark['doc']), (False, False)
        )

        # now test with json
        test_json_file = StringIO.StringIO()
        test_json_file.write(json_content)
        test_json_resource = TestHelpers.FakeFileStorage(test_json_file, "test.json")
        params = {
            'package_id': package['id'],
            'name': 'A JSON Resource',
            'upload': test_json_resource
        }
        result = test_helpers.call_action('resource_create', context, **params)
        dataset = test_helpers.call_action('package_show', id=package['id'])
        quality_mark = helpers.quality_mark(dataset)
        assert_equals(
            (quality_mark['machine'], quality_mark['doc']), (True, False)
        )

        # and with xml only
        del package
        package = factories.Dataset(owner_org=org['id'])
        test_xml_file = StringIO.StringIO()
        test_xml_file.write(xml_content)
        test_xml_resource = TestHelpers.FakeFileStorage(test_xml_file, "test.xml")

        params = {
            'package_id': package['id'],
            'name': 'An XMK Resource',
            'upload': test_xml_resource
        }

        result = test_helpers.call_action('resource_create', context, **params)
        dataset = test_helpers.call_action('package_show', id=package['id'])
        quality_mark = helpers.quality_mark(dataset)
        assert_equals(
            (quality_mark['machine'], quality_mark['doc']), (True, False)
        )

    def test_alphabetize_dict(self):
        tags_list = [
            {'count': 1, 
            'display_name': u'sat-scores', 
            'name': u'sat-scores'}, 
            {'count': 1, 
            'display_name': u'mathematics', 
            'name': u'mathematics'}, 
            {'count': 1, 
            'display_name': u'international-comparisons-of-achievement', 
            'name': u'international-comparisons-of-achievement'}, 
            {'count': 1, 'display_name': u'act-scores', 'name': u'act-scores'}
        ]
        excpeted_result = [
            {'count': 1, 'display_name': u'act-scores', 'name': u'act-scores'},
            {'count': 1, 
            'display_name': u'international-comparisons-of-achievement', 
            'name': u'international-comparisons-of-achievement'}, 
            {'count': 1, 
            'display_name': u'mathematics', 
            'name': u'mathematics'},               
            {'count': 1, 
            'display_name': u'sat-scores', 
            'name': u'sat-scores'}
        ]
        result = helpers.alphabetize_dict(tags_list)
        assert_equals(result, excpeted_result)
        





