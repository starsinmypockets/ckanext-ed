from __future__ import print_function

import sys
from pprint import pprint

from ckan import model
from ckan.logic import get_action
from ckan.plugins import toolkit

from ckan.lib.cli import CkanCommand


class Ed(CkanCommand):
    '''
 		Usage:
 		ed create_ed_vocabularies
 			- create vocabularies from json files
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 9
    min_args = 0

    def __init__(self, name):

        super(Ed, self).__init__(name)

        self.parser.add_option('-t', '--file_path', dest='file_path',
            default=False, help='Path to json file')


    def command(self):
        self._load_config()

        # We'll need a sysadmin user to perform most of the actions
        # We will use the sysadmin site user (named as the site_id)
        context = {'model': model, 'session': model.Session, 'ignore_auth': True}
        self.admin_user = get_action('get_site_user')(context, {})

        print('')

        if len(self.args) == 0:
            self.parser.print_usage()
            sys.exit(1)
        cmd = self.args[0]
        if cmd == 'create_ed_vocabularies':
            if len(self.args) > 1:
                self.create_ed_vocabularies()
            else:
	            self.parser.print_usage()

        else:
            print('Command {0} not recognized'.format(cmd))

    def _load_config(self):
        super(Ed, self)._load_config()


    def create_ed_vocabularies(self):

        if len(self.args) >= 1:
            name = unicode(self.args[1])
        else:
            print('Please provide a path to the file')
            sys.exit(1)

         ## Here we should do the read/load and create of vocabularies
