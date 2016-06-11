# encoding: utf-8
import json
from workflow import web, Workflow, PasswordNotFound

log = None

def get_projects(api_key):
    log.debug('Get Projects Started')
    """Retrieve all projects from 10.000ft

    Returns a list of project dictionaries.

    """ 
    
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
    #log.debug(url + '?' + params)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    
    # Parse the JSON returned by 10.000ft and extract the projects
    result = buffer.getvalue()
    result = json.loads(result)
    projects = result['data']

    log.debug('Number of projects fetched: ')
    log.debug(len(projects))
    
    return projects

def main(wf):
    try:
        # Get API key from Keychain
        api_key = wf.get_password('10k_api_key')

        # Retrieve posts from cache if available and no more than 600
        # seconds old

        def wrapper():
            """`cached_data` can only take a bare callable (no args),
            so we need to wrap callables needing arguments in a function
            that needs none.
            """
            return get_projects(api_key)

        posts = wf.cached_data('projects', wrapper, max_age=600)
        # Record our progress in the log file
        wf.logger.debug('{} projects cached from 10.000ft'.format(len(posts)))

    except PasswordNotFound:  # API key has not yet been set
        # Nothing we can do about this, so just log it
        wf.logger.error('No API key saved')

if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    wf.run(main)