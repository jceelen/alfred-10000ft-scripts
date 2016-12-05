#!/usr/bin/python
# encoding: utf-8

# About encoding: 
# Best practice in Python programs is to use Unicode internally and decode all 
# text input and encode all text output at IO boundaries (i.e. right where it 
# enters/leaves your program). On OS X, UTF-8 is almost always the right encoding.

# Because we want to work with Unicode, it's simpler if we make
# literal strings in source code Unicode strings by default, so
# we set `encoding: utf-8` at the very top of the script to tell Python
# that this source file is UTF-8 and import `unicode_literals` before any
# code.
#
# See Tip further down the page for more info
from __future__ import unicode_literals

import subprocess
from workflow import web, Workflow, PasswordNotFound


def get_projects(api_key):
    """Retrieve all projects from 10.000ft
    Returns a list of project dictionaries.
    """ 
    
    import json
    from lib import pycurl    
    from StringIO import StringIO
    from urllib import urlencode

    buffer = StringIO()

    #Set variables, TODO: From is not working?
    url = 'https://api.10000ft.com/api/v1/projects/'
    params = {'auth' : api_key,
              #'from' : '2016-01-01',
              #'to' : '',
              'fields' : 'tags, budget_items, project_state, phase_count',
              #'filter_field' : 'project_state',    #The property to filter on
              #'filter_list' : '',  #Options: Internal, Tentative, Confirmed
              'sort_field' : 'updated',
              'sort_order' : 'descending',
              #'project_code' : '',
              #'phase_name' : '',
              #'with_archived' : 'false',
              #'with_phases' : 'false',
              'per_page' : 10000,
              }
    params = urlencode(params)                

    #Do the request
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
      # If the value of client is None this can cause problems, let's find them
      if project['client'] is None:
        # replace none values with an empty string
        project['client'] = ''

    # Return projects as a library with updated data
    return projects

def main(wf):
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

        projects = wf.cached_data('projects', wrapper, max_age=600)
        # Record our progress in the log file
        wf.logger.info('{} projects cached from 10.000ft'.format(len(projects)))

    except PasswordNotFound:  # API key has not yet been set
        # Nothing we can do about this, so just log it
        wf.logger.error('No API key saved')

if __name__ == '__main__':
    wf = Workflow()
    wf.run(main)