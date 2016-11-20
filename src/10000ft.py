# encoding: utf-8
import sys
import argparse
from urllib import urlencode, unquote_plus, quote_plus, quote
from workflow import (Workflow, PasswordNotFound)
from workflow.background import run_in_background, is_running

# Update data
UPDATE_SETTINGS = {'github_slug': 'jceelen/alfred-10000ft-scripts'}
ICON_UPDATE = 'icons/update_available.png'

# Shown in error logs. Users can find help here
HELP_URL = 'https://github.com/jceelen/alfred-10000ft-scripts/issues'

log = None

def search_key_for_project(project):
    """Generate a string search key for a post"""
    elements = []
    elements.append(project['name'])  # projectnaam
    #DISABLED because client is generating an error# elements.append(project['client'])  # klant
    elements.append(project['project_state'])  # status
    elements.append(str(project['project_code']))  # projectcode
    return u' '.join(elements)


def get_project_data(project_id):
    """Find the project matching the project_id"""
    projects = wf.cached_data('projects', None, max_age=0)
        
    #loop through projects and return project with a match
    for project in projects:     
        if int(project['id']) == int(project_id):
            return project

def add_project(project):
    wf.add_item(title=project['name'],
            subtitle='ENTER to view project, press ALT to show more info.',
            modifier_subtitles={
                #'shift': 'Subtext when shift is pressed',
                #'fn': 'Subtext when ctrl is pressed',
                # DISABLED because client is generating an error# 'alt': 'Client: ' + project['client'] + ' | Tags: ' + str(taglist),
                'ctrl': 'View in 10.000ft',
                'cmd': 'Edit in 10.000ft, CMD+C to copy name.'
                },
            arg=str(project['id']),
            valid=True,
            icon='icons/project_{0}.png'.format(project['project_state']).lower(),
            copytext=project['name'])

def build_taglist(tags):
    taglist = []
    for tag in tags:
        taglist.append(tag['value'].lower())    
    return taglist

def build_report_params(view, project):
    from datetime import datetime
    now = datetime.now()
    
    params = [('view', view), #8 = Fees, 10 = hours
              ('time', 4),
              ('start', project['starts_at']),
              ('end', project['ends_at']),
              ('firstgroup', 'phase_name'),
              ('secondgroup', 'user_name'),
              ('filters', '[["' + project['name'] + '"],[],["' + project['client'] + '"],[],[],[],[],["Confirmed","Future"],[],[],[],[],[],[]]'),
              ('version', 2),
              ('title', 'Rapportage: ' + project['name'] + ' - %s-%s-%s' % (now.day, now.month, now.year))
            ]
    params = urlencode(params)
    #wf.logger.debug('PARAMS: https://app.10000ft.com/reports?' + params)
    
    return str('reports?' + params)

"""
def update_project(project_id):
    #Update specific project in 10.000ft
    
    import json
    from lib import pycurl    
    from StringIO import StringIO

    buffer = StringIO()

    #try?
    api_key = wf.get_password('10k_api_key')

    url = 'https://api.10000ft.com/api/v1/projects/' + project_id
    params = {'auth' : api_key
              #'from' : '2016-01-01',
              #'to' : '',
              #'fields' : 'tags, budget_items, project_state, phase_count',
              #'filter_field' : 'project_state',    #The property to filter on
              #'filter_list' : '',  #Options: Internal, Tentative, Confirmed
              #'sort_field' : 'updated',
              #'sort_order' : 'descending',
              #'project_code' : '',
              #'phase_name' : '',
              #'with_archived' : 'false',
              #'with_phases' : 'false',
              #'per_page' : 10000,
              }
    params = urlencode(params)                

    data = json.dumps({"id" : project_id, "archived" : "true"})
    
    #wf.logger.debug('url: ' str(url + '?' + params))
    #wf.logger.debug('data: ' str(data))

    #Do the request
    c = pycurl.Curl()
    c.setopt(c.URL, url + '?' + params) 
    c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json'])
    c.setopt(pycurl.CUSTOMREQUEST, "PUT")
    c.setopt(pycurl.POSTFIELDS,data)
    c.perform()
    c.close()
"""

def main(wf):   
    wf.logger.info('main started')
    
    # Update available?
    if wf.update_available:
        wf.add_item('A newer version is available',
                    'Press ENTER to install update',
                    autocomplete='workflow:update',
                    icon='update_available.png')


    ####################################################################
    # Get arguments
    ####################################################################

    # Build argument parser to parse script args and collect their values
    parser = argparse.ArgumentParser()

    # If --setkey is added as an argument, add an optional (nargs='?') and save its value to 'apikey' (dest). 
    # This will be called from a separate "Run Script" action with the API key
    parser.add_argument('--setkey', dest='apikey', nargs='?', default=None)
    # If --setuser is added as an argument, save its value to 'user' (dest)
    # This will be used to safe the tag of the user in wf.settings
    parser.add_argument('--setuser', dest='user', nargs='?', default=None)

    # If --user is added as an argument, save its value to 'user_tag' (dest)
    # This will be used to show the list of projects for that user (based on tags)
    parser.add_argument('--user', dest='user_tag', nargs='?', default=None)

    # If --options is added as an argument, save its value to 'project_id' (dest)
    # This will be used to show the list of options for the selected project
    parser.add_argument('--options', dest='project_id', nargs='?', default=None)
    
    # Add an optional query and save it to 'query'
    parser.add_argument('query', nargs='?', default=None)
    
    # Parse the script's arguments
    args = parser.parse_args(wf.args)


    ####################################################################
    # Process arguments if possible
    ####################################################################

    if args.apikey:  # Script was passed an API key
        # Save the provided API key
        wf.save_password('10k_api_key', args.apikey)
        return 0  # 0 means script exited cleanly
    if args.user:  # Script was passed a username
        # save the user
        wf.settings['user'] = args.user.lower()
        return 0  # 0 means script exited cleanly
    

    ####################################################################
    # Check that we have an API key saved
    ####################################################################

    try:
        wf.get_password('10k_api_key')
    except PasswordNotFound:  # API key has not yet been set
        wf.add_item('No API key set.',
                    'Please use .10ksetkey to set your 10.000ft API key.',
                    valid=False,
                    icon='icons/warning.png')
        wf.send_feedback()
        return 0


    ####################################################################
    # Get data and filter 10.000ft projects
    ####################################################################

    # Get query from Alfred
    query = args.query
    
    # Get posts from cache. Set `data_func` to None, as we don't want to
    # update the cache in this script and `max_age` to 0 because we want
    # the cached data regardless of age
    projects = wf.cached_data('projects', None, max_age=0)

    # Start update script if cached data is too old (or doesn't exist)
    if not wf.cached_data_fresh('projects', max_age=600):
        cmd = ['/usr/bin/python', wf.workflowfile('update.py')]
        run_in_background('update', cmd)

    # Notify the user if the cache is being updated
    if is_running('update'):
        wf.add_item('Fetching data from 10.000ft...',
                    valid=False,
                    icon='icons/fetching_data.png')
    
    # If script was passed a query, use it to filter projects
    if query and projects:
        projects = wf.filter(query, projects, key=search_key_for_project, min_score=20)

    # If we have no data to show, so show a warning and stop
    if not projects:  
        wf.add_item('No projects found', icon='icons/warning.png')
        wf.send_feedback()
        return 0


    ####################################################################
    # Show options for project
    ####################################################################

    # If argument --options is passed on, show the options for manipulating a project.
    if wf.args[0] == '--options':
        # Get current project data
        project = get_project_data(args.project_id)
        report_time = build_report_params(10, project).encode('utf-8')
        report_fees = build_report_params(8, project).encode('utf-8')
        # Add options for projects 
        wf.add_item(title='View project',
                    subtitle=project['name'],
                    arg='viewproject?id=' + str(project['id']),
                    valid=True,
                    icon='icons/project_view.png'
                    )
        wf.add_item(title='Edit project',
                    subtitle=project['name'],
                    arg='editproject?id=' + str(project['id']),
                    valid=True,
                    icon='icons/project_edit.png'
                    )
        wf.add_item(title='Budget report time for project',
                    subtitle=project['name'],
                    arg=report_time,
                    copytext='https://app.10000ft.com/' + str(build_report_params(10, project)),
                    valid=True,
                    icon='icons/project_budget_report_time.png'
                    )
        wf.add_item(title='Budget report fees for project',
                    subtitle=project['name'],
                    arg=report_fees,
                    copytext='https://app.10000ft.com/' + str(build_report_params(8, project)),
                    valid=True,
                    icon='icons/project_budget_report_fees.png'
                    )
        wf.add_item(title='WIP: Archive Project',
                    subtitle=project['name'],
                    arg=report_fees,
                    copytext='https://app.10000ft.com/' + str(build_report_params(8, project)),
                    valid=True,
                    icon='icons/project_budget_report_fees.png'
                    )
        wf.send_feedback()


    ####################################################################
    # Show List of projects
    ####################################################################

    # Get the user tag from wf.settings
    user_tag = wf.settings['user']

    # Loop through the returned projects and add an item for each to the list of results for Alfred
    for project in projects:
        # Extract tags from data and put them in a list
        taglist = build_taglist(project['tags']['data'])
        # Only show projects of current user if the argument --user is passed on
        # TODO: show errormessage if wf.settings['user'] is empty
        if wf.args[0] == '--user':
            # Check if the current user_tag is in the list of tags for this project.
            if user_tag in taglist:
                # Add the project to the list as an item
                add_project(project)
        else:
            # Add the project to the list as an item           
            add_project(project)
    # Send the results to Alfred as XML
    wf.send_feedback()
    return 0


if __name__ == '__main__':
    wf = Workflow(help_url=HELP_URL,
                  update_settings=UPDATE_SETTINGS)
    log = wf.logger
    sys.exit(wf.run(main))
