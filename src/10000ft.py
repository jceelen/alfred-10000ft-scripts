#!/usr/bin/python
# encoding: utf-8

# About encoding: 
# Best practice in Python programs is to use Unicode internally and decode all 
# text input and encode all text output at IO boundaries (i.e. right where it 
# enters/leaves your program). On OS X, UTF-8 is almost always the right 
# encoding. 
# Be sure to decode all input from and encode all output to the system 
# (in particular via subprocess and when passing a {query} to a subsequent 
# workflow action).

# Because we want to work with Unicode, it's simpler if we make
# literal strings in source code Unicode strings by default, so
# we set `encoding: utf-8` at the very top of the script to tell Python
# that this source file is UTF-8 and import `unicode_literals` before any
# code.
from __future__ import unicode_literals, print_function

import sys
import argparse
import subprocess
from urllib import urlencode, quote
from workflow import (Workflow, PasswordNotFound)
from workflow.background import run_in_background, is_running
#import os

# Update data
UPDATE_SETTINGS = {'github_slug': 'jceelen/alfred-10000ft-scripts'}
ICON_UPDATE = 'icons/update_available.png'

# Shown in error logs. Users can find help here
HELP_URL = 'https://github.com/jceelen/alfred-10000ft-scripts/issues'

log = None

# function for debugging purposes, it determines the type of a variable
# wf.logger.debug('YOURVARIABLE is a: ' + whatisthis(yourvariable))
def whatisthis(s, name):
    if isinstance(s, str):
        result = 'ordinary string'
    elif isinstance(s, unicode):
        result = 'unicode string'
    else:
        result = 'not a string but a: ' + str(type(s))

    return wf.logger.debug('your variable ' + name + ' is a: ' + result)

def search_key_for_project(project):
    """Generate a string search key for a post"""
    elements = []
    elements.append(project['name'])  # projectnaam
    elements.append(project['client'])  # klant
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
                'alt': 'Client: ' + project['client'] + ' | Tags: ',# + str(taglist),
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
              ('title', 'Report: ' + project['name'] + ' - %s-%s-%s' % (now.day, now.month, now.year))
            ]
    params = urlencode(params)
    #wf.logger.debug('PARAMS: https://app.10000ft.com/reports?' + params)
    
    return str('https://app.10000ft.com/reports?' + params)


def toggle_archive_project(project_id):
    wf.logger.info('started function toggle_archive_project')
    #Update specific project in 10.000ft
    import json
    from lib import pycurl

    #try?
    api_key = wf.get_password('10k_api_key')

    url = 'https://api.10000ft.com/api/v1/projects/' + str(project_id) + '?auth=' +str(api_key)
    #wf.logger.debug('url: ' + str(url))
    
    data = json.dumps({"id" : project_id, "archived" : "true"})
    #wf.logger.debug('data: ' + str(data))

    #Do the request
    c = pycurl.Curl()
    c.setopt(c.URL, url) 
    c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json'])
    c.setopt(pycurl.CUSTOMREQUEST, "PUT")
    c.setopt(pycurl.POSTFIELDS,data)
    c.perform()
    c.close()
    wf.logger.info('finished function toggle_archive_project')


def toggle_delete_project(project_id):
    wf.logger.info('started function toggle_delete_project')
    #Update specific project in 10.000ft
    import json
    from lib import pycurl

    #try?
    api_key = wf.get_password('10k_api_key')

    url = 'https://api.10000ft.com/api/v1/projects/' + str(project_id) + '?auth=' +str(api_key)
    data = json.dumps({})
    #wf.logger.debug('url: ' + str(url))
    
    #Do the request
    c = pycurl.Curl()
    c.setopt(c.URL, url) 
    c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json'])
    c.setopt(pycurl.CUSTOMREQUEST, "DELETE")
    c.setopt(pycurl.POSTFIELDS, data)
    c.perform()
    c.close()
    wf.logger.info('finished function toggle_delete_project')


def main(wf):   
    wf.logger.info('started main')
    
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
    
    # If --toggle_archive_project is added as an argument, save its value to 'project_id' (dest)
    # This will be used toggle the archived status for the selected project
    parser.add_argument('--toggle_archive_project', dest='project_id', nargs='?', default=None)
    parser.add_argument('--toggle_delete_project', dest='project_id', nargs='?', default=None)

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

    # If argument --toggle_archive_project is passed on update the project.
    if wf.args[0] == '--toggle_archive_project':
        wf.logger.info('started  --toggle_archive_project')
        #wf.logger.debug(args.project_id)
        toggle_archive_project(args.project_id)
        return 0  # 0 means script exited cleanly
    if wf.args[0] == '--toggle_delete_project':
        wf.logger.info('started  --toggle_delete_project')
        #wf.logger.debug(args.project_id)
        toggle_delete_project(args.project_id)

        #TODO add call for updating data or delete from cache? http://alfredworkflow.readthedocs.io/en/latest/user-manual/persistent-data.html?highlight=cache#clearing-cached-data 

        return 0  # 0 means script exited cleanly

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
        wf.logger.info('started building options menu')
        project = get_project_data(args.project_id)
        report_time = build_report_params(10, project).encode('utf-8')
        report_fees = build_report_params(8, project).encode('utf-8')
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
                    arg='10000ft.py --toggle_archive_project ' + str(project['id']),
                    valid=True,
                    icon='icons/project_archive.png'
                    )
        wf.add_item(title='Delete project',
            subtitle=project['name'],
            arg='10000ft.py --toggle_delete_project ' + str(project['id']),
            valid=True,
            icon='icons/project_delete.png'
            )
        """wf.add_item(title='Unarchive project',
        subtitle=project['name'],
        arg='10000ft.py --toggle_archive_project ' + str(project['id']),
        valid=True,
        icon='icons/project_unarchive.png'
        )"""
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


if __name__ == u'__main__':
    wf = Workflow(help_url=HELP_URL,
                  update_settings=UPDATE_SETTINGS)
    log = wf.logger
    sys.exit(wf.run(main))