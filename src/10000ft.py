# encoding: utf-8
import sys
import argparse
from workflow import (Workflow, ICON_WEB, ICON_INFO, ICON_WARNING, PasswordNotFound)
from workflow.background import run_in_background, is_running

UPDATE_SETTINGS = {
    # Your username and the workflow's repo's name
    'github_slug': 'jceelen/alfred-10000ft-scripts',
    'frequency': 7
    }
HELP_URL = 'https://github.com/jceelen/alfred-10000ft-scripts/issues'

log = None


def search_key_for_project(project):
    """Generate a string search key for a post"""
    elements = []
    elements.append(project['name'])  # projectnaam
    elements.append(project['client'])  # klant
    elements.append(str(project['project_code']))  # projectcode
    return u' '.join(elements)



def main(wf):
    log.debug('Main Started')
    # build argument parser to parse script args and collect their
    # values
    parser = argparse.ArgumentParser()
    # add an optional (nargs='?') --setkey argument and save its
    # value to 'apikey' (dest). This will be called from a separate "Run Script"
    # action with the API key
    parser.add_argument('--setkey', dest='apikey', nargs='?', default=None)
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
    # Check for update
    if (wf.update_available and
            wf.settings.get('show_update_notification', True)):
        wf.add_item('Update available',
                    '↩ to install update',
                    autocomplete='workflow:update',
                    icon='icons/update-available.png')

    # Get query from Alfred
    query = args.query
    
    # Get posts from cache. Set `data_func` to None, as we don't want to
    # update the cache in this script and `max_age` to 0 because we want
    # the cached data regardless of age
    projects = wf.cached_data('projects', None, max_age=0)

    # Start update script if cached data is too old (or doesn't exist)
    if not wf.cached_data_fresh('posts', max_age=600):
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

    if not projects:  # we have no data to show, so show a warning and stop
        wf.add_item('No projects found', icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    # Loop through the returned projects and add an item for each to
    # the list of results for Alfred
    for project in projects:
        wf.add_item(title=project['name'],
                    subtitle='Client: ' + project['client'] + '. Project state: ' + project['project_state'],
                    modifier_subtitles={
                        #'shift': 'Subtext when shift is pressed',
                        #'fn': 'Subtext when fn is pressed',
                        #'ctrl': 'Subtext when ctrl is pressed',
                        'alt': 'tags: ' + str(project['tags']['data']),
                        'cmd': 'id: ' + str(project['id']) + 'guid: ' + project['guid']
                    },
                    arg=str(project['id']),
                    valid=True,
                    icon=ICON_WEB,
                    copytext=project['name'])
    
    # Send the results to Alfred as XML
    wf.send_feedback()
    return 0

if __name__ == u"__main__":
    wf = Workflow(update_settings=UPDATE_SETTINGS, help_url=HELP_URL)
    log = wf.logger
    sys.exit(wf.run(main))
