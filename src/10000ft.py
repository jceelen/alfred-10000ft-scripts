#!/usr/bin/python
# encoding: utf-8

from __future__ import unicode_literals, print_function

import sys
import argparse
#import subprocess
from urllib import urlencode, quote
from workflow import (Workflow, PasswordNotFound, )
from workflow.background import run_in_background, is_running
from workflow.notify import notify

# Update data
UPDATE_SETTINGS = {'github_slug': 'jceelen/alfred-10000ft-scripts'}
ICON_UPDATE = 'icons/update_available.png'

# Shown in error logs. Users can find help here
HELP_URL = 'https://github.com/jceelen/alfred-10000ft-scripts/issues'

log = None

def whatisthis(s, name):
    """For debugging it determines the type of a variable."""
    if isinstance(s, str):
        result = 'ordinary string'
    elif isinstance(s, unicode):
        result = 'unicode string'
    else:
        result = 'not a string but a: ' + str(type(s))

    return wf.logger.debug('your variable ' + name + ' is a: ' + result)

def search_key_for_project(project):
    """Generate a string search key for a post."""
    elements = []
    elements.append(project['name'])
    elements.append(project['client'])
    elements.append(project['project_state'])
    elements.append(str(project['project_code']))
    return u' '.join(elements)

def get_project_data(project_id):
    """Find the project matching the project_id."""
    projects = wf.cached_data('projects', None, max_age=0)
        
    # Loop through projects and return project with a match
    for project in projects:     
        if int(project['id']) == int(project_id):
            return project

def add_project(project):
    """Add project as an item to show in Alfred."""
    wf.add_item(title=project['name'],
            subtitle='ENTER to view project, press ALT to show more info.',
            modifier_subtitles={
                'alt': 'Client: ' + project['client'],# + ' | Tags: ' + str(taglist),
                'ctrl': 'View in 10.000ft',
                'cmd': 'Edit in 10.000ft, CMD+C to copy name.'
                },
            arg=str(project['id']),
            valid=True,
            icon='icons/project_{0}.png'.format(project['project_state']).lower(),
            copytext=project['name'])

def build_taglist(tags):
    """Generate a list of tags."""
    taglist = []
    for tag in tags:
        taglist.append(tag['value'].lower())    
    return taglist

def build_report_params(view, project):
    """Generate a string that contains the URL to a report."""
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
              ('title', 'Report: ' + project['name'] + ' - %s-%s-%s' % (now.day, now.month, now.year))
            ]

    params = urlencode(params).encode('utf-8')
    # Temporary fix to replace + with %20
    params = params.replace('+', '%20')
    url = 'https://app.10000ft.com/reports?' + params
    # Output the time report URL for debug purposes
    #if view is 10:
        #wf.logger.debug('URL for debugging purposes: ' + url)
    
    return url

def project_filter(filename):
    """Filter needed for deleting projects cache."""
    return 'projects' in filename

def update_project(project_id, action):
    """Update specific project in 10.000ft."""
    wf.logger.info('Started updating project')
    
    import json
    from lib import pycurl
    from StringIO import StringIO

    buffer = StringIO()

    # Set access variables
    api_key = wf.get_password('10k_api_key')
    url = 'https://api.10000ft.com/api/v1/projects/' + str(project_id) + '?auth=' +str(api_key)  

    # Determine other variables based on the action
    if action == 'archive_project':
        data = json.dumps({"id" : project_id, "archived" : "true"})
        request_method = "PUT"
        status = 'Archived: '
    if action == 'delete_project':
        data = json.dumps({})
        request_method = "DELETE"
        status = 'Deleted: '

    # Do the request
    c = pycurl.Curl()
    c.setopt(c.URL, url) 
    c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json'])
    c.setopt(pycurl.CUSTOMREQUEST, request_method)
    c.setopt(pycurl.POSTFIELDS,data)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    
    # Capture the response and store the json in a dictionary
    result = buffer.getvalue()
    project = json.loads(result)
    wf.logger.debug('Finished and processed request to 10.000ft, result: ' + str(project))

    # Finishing up based on response from 10.000ft
    if 'id' in project:
        # If everything goes well 10.000ft returns all the updated project info
        notify_title = 'Your project is updated!'
        notify_text = status + project['name']
        
        # Clear cache
        wf.clear_cache(project_filter)

        # Update cache
        cmd = ['/usr/bin/python', wf.workflowfile('update.py')]
        run_in_background('update', cmd)

    elif 'message' in project:
        # 10.000ft returns a message if something went wrong
        notify_title = 'Something went wrong :-/)'
        notify_text = project['message']
        wf.logger.info('Something went wrong :-/. Message from 10.000ft: ' + str(project['message']))

    else:
        notify_title = 'An error occured :-/)'
        notify_text = 'Check the log files for mor information'
    
    return notify(notify_title, notify_text)

####################################################################
# Alfred Workflow Main
####################################################################

def main(wf):   
    wf.logger.info('Started main')
    
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
    # This will be called from a separate 'Run Script' action with the API key
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
    
    # If --archive_project is added as an argument, save its value to 'project_id' (dest)
    # This will be used toggle the archived status for the selected project
    parser.add_argument('--archive_project', dest='project_id', nargs='?', default=None)
    parser.add_argument('--delete_project', dest='project_id', nargs='?', default=None)

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
    # Update projects
    ####################################################################

    if wf.args[0] == '--archive_project':
    # Archive project if --archive_project
        update_project(args.project_id, 'archive_project')
        return 0
    
    if wf.args[0] == '--delete_project':
    # Delete project if --delete_project
        update_project(args.project_id, 'delete_project')
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
        wf.logger.info('Started building options menu')
        project = get_project_data(args.project_id)
        
        # Build report URLs
        report_time = build_report_params(10, project)
        report_fees = build_report_params(8, project)
    
        # Add options for projects 
        wf.add_item(title='View project',
                    subtitle=project['name'],
                    arg='https://app.10000ft.com/viewproject?id=' + str(project['id']),
                    valid=True,
                    icon='icons/project_view.png'
                    )
        wf.add_item(title='Edit project',
                    subtitle=project['name'],
                    arg='https://app.10000ft.com/editproject?id=' + str(project['id']),
                    valid=True,
                    icon='icons/project_edit.png'
                    )
        wf.add_item(title='Budget report time for project',
                    subtitle=project['name'],
                    arg=report_time,
                    valid=True,
                    icon='icons/project_budget_report_time.png'
                    )
        wf.add_item(title='Budget report fees for project',
                    subtitle=project['name'],
                    arg=report_fees,
                    valid=True,
                    icon='icons/project_budget_report_fees.png'
                    )
        wf.add_item(title='Archive project',
                    subtitle=project['name'],
                    arg='10000ft.py --archive_project ' + str(project['id']),
                    valid=True,
                    icon='icons/project_archive.png'
                    )
        wf.add_item(title='Delete project',
                    subtitle=project['name'],
                    arg='10000ft.py --delete_project ' + str(project['id']),
                    valid=True,
                    icon='icons/project_delete.png'
                    )
        wf.send_feedback()


    ####################################################################
    # Show List of projects
    ####################################################################
    else:
        # Get the user tag from wf.settings
        user_tag = wf.settings['user']

        # Loop through the returned projects and add an item for each to the list of results for Alfred
        for project in projects:
            # Extract tags from data and put them in a list
            taglist = build_taglist(project['tags']['data'])
            # Only show projects of current user if the argument --user is passed on
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