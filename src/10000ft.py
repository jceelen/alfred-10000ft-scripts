# encoding: utf-8
import sys
import argparse
from urllib import urlencode, unquote_plus
from workflow import (Workflow, ICON_WEB, ICON_INFO, ICON_WARNING, PasswordNotFound)
from workflow.background import run_in_background, is_running

# Update data
UPDATE_SETTINGS = {'github_slug': 'jceelen/alfred-10000ft-scripts'}
ICON_UPDATE = 'update-available.png'

# Shown in error logs. Users can find help here
HELP_URL = 'https://github.com/jceelen/alfred-10000ft-scripts/issues'

log = None

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

def main(wf):   
    wf.logger.info('main started')
    # Update available?
    if wf.update_available:
        wf.add_item('A newer version is available',
                    'Press ENTER to install update',
                    autocomplete='workflow:update',
                    icon=ICON_UPDATE)

    # build argument parser to parse script args and collect their
    # values
    parser = argparse.ArgumentParser()
    # add an optional (nargs='?') --setkey argument and save its
    # value to 'apikey' (dest). This will be called from a separate "Run Script"
    # action with the API key
    parser.add_argument('--setkey', dest='apikey', nargs='?', default=None)
    parser.add_argument('--setuser', dest='user', nargs='?', default=None)
    parser.add_argument('--options', dest='project_id', nargs='?', default=None)
    # add an optional query and save it to 'query'
    parser.add_argument('query', nargs='?', default=None)
    # parse the script's arguments
    args = parser.parse_args(wf.args)

    ####################################################################
    # Save the provided API key
    ####################################################################

    # decide what to do based on arguments
    if args.apikey:  # Script was passed an API key
        # save the key
        wf.save_password('10k_api_key', args.apikey)
        return 0  # 0 means script exited cleanly
    if args.user:  # Script was passed an API key
        # save the key
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
                    icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    ####################################################################
    # View/filter 10.000ft projects
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
        wf.add_item('Getting new projects from 10.000ft',
                    valid=False,
                    icon=ICON_INFO)
    
    # If script was passed a query, use it to filter projects
    if query and projects:
        projects = wf.filter(query, projects, key=search_key_for_project, min_score=20)

    # we have no data to show, so show a warning and stop
    if not projects:  
        wf.add_item('No projects found', icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    ####################################################################
    # Show options for project
    ####################################################################

    # If project_id was passed on in the query, show the options for manipulating a project.
    if args.project_id:
        from datetime import datetime
        now = datetime.now()

        # Get current project data
        project = get_project_data(args.project_id)

        # Build report URL
        params = {'view' : 10, #8 = Fees, 10 = hours
                  'time' : 4,
                  'start' : project['starts_at'],
                  'end' : project['ends_at'],
                  'firstgroup' : 'phase_name',
                  'secondgroup' : 'user_name',
                  'filters' : '[["' +project['name']+ '"],[],["' +project['client']+ '"],[],[],[],[],["Confirmed","Future"],[],[],[],[],[],[]]',
                  'version' : 2,
                  'title' : project['name'] + ' - %s-%s-%s' % (now.day, now.month, now.year)
                    }

        params = unquote_plus(urlencode(params))
        wf.logger.debug('reports?' + params)

        # Add options for projects 
        wf.add_item(title='View project',
                    subtitle=project['name'],
                    arg='viewproject?id=' + str(project['id']),
                    valid=True,
                    icon='icons/icon_project_{0}.png'.format(project['project_state']).lower())
        wf.add_item(title='Edit project',
                    subtitle=project['name'],
                    arg='editproject?id=' + str(project['id']),
                    valid=True,
                    icon='icons/icon_project_{0}.png'.format(project['project_state']).lower())
        wf.add_item(title='Run report for project',
                    subtitle=project['name'],
                    arg='reports?' + params,
                    valid=True,
                    icon='icons/icon_project_{0}.png'.format(project['project_state']).lower())
        wf.send_feedback()

    # Show list of projects
    else: 
        # Loop through the returned projects and add an item for each to
        # the list of results for Alfred
        for project in projects:
            
            # WIP Extract tags from data for every project and put them in a list
            tags = project['tags']['data']
            taglist = []
            for tag in tags:
                taglist.append(tag['value'])
            
            wf.add_item(title=project['name'],
                        subtitle='ENTER to view project, press ALT to show more info.',
                        modifier_subtitles={
                            #'shift': 'Subtext when shift is pressed',
                            #'fn': 'Subtext when ctrl is pressed',
                            'alt': 'Client: ' + project['client'] + ' | Tags: ' + str(taglist),
                            'ctrl': 'View in 10.000ft',
                            'cmd': 'Edit in 10.000ft, CMD+C to copy name.'
                            },
                        arg=str(project['id']),
                        valid=True,
                        icon='icons/icon_project_{0}.png'.format(project['project_state']).lower(),
                        copytext=project['name'])
        
        # Send the results to Alfred as XML
        wf.send_feedback()
        return 0


if __name__ == '__main__':
    wf = Workflow(help_url=HELP_URL,
                  update_settings=UPDATE_SETTINGS)
    log = wf.logger
    sys.exit(wf.run(main))
