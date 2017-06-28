#!/usr/bin/python
# encoding: utf-8

from __future__ import unicode_literals

import argparse
from workflow import Workflow, PasswordNotFound


def get_projects(api_key):
    """Retrieve all projects from 10.000ft
    Returns a list of project dictionaries.
    """
    import json
    from lib import pycurl
    from StringIO import StringIO
    from urllib import urlencode

    buffer = StringIO()

    # Set variables
    url = 'https://api.10000ft.com/api/v1/projects/'
    params = {'auth': api_key,
              # 'from' : '2016-01-01',
              # 'to' : '',
              'fields': 'tags, budget_items, project_state, phase_count',
              # 'filter_field' : 'project_state',    #The property to filter on
              # 'filter_list' : '',  #Options: Internal, Tentative, Confirmed
              'sort_field': 'updated',
              'sort_order': 'descending',
              # 'project_code' : '',
              # 'phase_name' : '',
              # 'with_archived' : 'false',
              # 'with_phases' : 'false',
              'per_page': 10000,
              }
    params = urlencode(params, 'utf-8')

    # Do the request
    c = pycurl.Curl()
    c.setopt(c.URL, url + '?' + params)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    # Parse the JSON returned by 10.000ft and extract the projects
    result = buffer.getvalue()
    result = json.loads(result)

    # Store the result in a projects library
    projects = result['data']

    # Cycle through projects to modify data if necessary
    for project in projects:
        # If the value of client is None this causes problems, let's find them
        if project['client'] is None:
            # replace none values with an empty string
            project['client'] = ''

    # Return projects as a library with updated data
    return projects


def get_clients(api_key):
    """Retrieve all client tags from 10.000ft
    Returns a list of client tag dictionaries.
    """
    import json
    from lib import pycurl
    from StringIO import StringIO
    from urllib import urlencode

    buffer = StringIO()

    # Set variables
    url = 'https://api.10000ft.com/api/v1/tags'
    params = {'auth': api_key,
              'unique': 'true',
              'namespace': 'client',
              'minimal_response': 'true',
              'sort_order': 'descending',
              'page': 1,
              'per_page': 10000,
              }

    params = urlencode(params, 'utf-8')

    # Do the request
    c = pycurl.Curl()
    c.setopt(c.URL, url + '?' + params)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    # Parse the JSON returned by 10.000ft and extract the clients
    result = buffer.getvalue()
    result = json.loads(result)

    # Store the result in a projects library
    clients = result['data']

    # Return projects as a library with updated data
    return clients


def main(wf):
    ####################################################################
    # Get and Parse arguments
    ####################################################################

    # Build argument parser to parse script args and collect their values
    parser = argparse.ArgumentParser()

    # Check if the a force argument is parced and set the max_age
    parser.add_argument('--update', dest='update_method',
                        nargs='?', default='normal')

    args = parser.parse_args(wf.args)

    wf.logger.info('update_method = ' + args.update_method)

    ####################################################################
    # Run argument-specific actions
    ####################################################################

    if args.update_method == 'force':
        max_age = 1
    else:
        max_age = 600

    ####################################################################
    # Get data the data from 10.000ft
    ####################################################################

    try:
        # Get API key from Keychain
        api_key = wf.get_password('10k_api_key')

        # Retrieve projects from cache if available and no more than 600
        # seconds old

        def wrapper():
            """`cached_data` can only take a bare callable (no args),
            so we need to wrap callables needing arguments in a function
            that needs none.
            """
            return get_projects(api_key)

        # Get the new data
        projects = wf.cached_data('projects', wrapper, max_age=max_age)

        # Record our progress in the log file
        wf.logger.info('{} projects cached, max_age {} second(s)'.format(
            len(projects), max_age))

    except PasswordNotFound:  # API key has not yet been set
        # Nothing we can do about this, so just log it
        wf.logger.error('No API key saved')

    try:
        # Get API key from Keychain
        api_key = wf.get_password('10k_api_key')

        # Retrieve projects from cache if available and no more than 600
        # seconds old

        def wrapper():
            """`cached_data` can only take a bare callable (no args),
            so we need to wrap callables needing arguments in a function
            that needs none.
            """
            return get_clients(api_key)

        # Get the new data
        clients = wf.cached_data('clients', wrapper, max_age=max_age)
        # Record our progress in the log file
        wf.logger.info('{} clients cached, max_age {} second(s)'.format(
            len(clients), max_age))

    except PasswordNotFound:  # API key has not yet been set
        # Nothing we can do about this, so just log it
        wf.logger.error('No API key saved')
if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    wf.run(main)
