#!/usr/bin/python
# encoding: utf-8

from __future__ import unicode_literals, print_function

import sys
import argparse
from urllib import urlencode
from workflow import (Workflow, PasswordNotFound)
from workflow.background import run_in_background, is_running
from workflow.notify import notify

# Update data
UPDATE_SETTINGS = {'github_slug': 'jceelen/alfred-10000ft-scripts'}
ICON_UPDATE = 'icons/update_available.png'

# Shown in error logs. Users can find help here
HELP_URL = 'https://github.com/jceelen/alfred-10000ft-scripts/issues'

log = None
anonymize = False


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


def get_client_data(client_name):
    """Find the client matching the client_name."""
    wf.logger.debug('starting get_client_data')
    clients = wf.cached_data('clients', None, max_age=0)

    # Loop through clients and return client with a match
    for client in clients:
        if client['name'] == client_name:
            wf.logger.debug('get_client_id finished, client_data: ' + str(client))
            return client


def add_project(project, taglist):
    """Add project as an item to show in Alfred."""
    if anonymize:
        import random
        project['name'] = 'Anonimized Project ' + str(project['id'])[-3:]
        project['client'] = 'Anonimized Client'

    wf.add_item(title=project['name'],
                subtitle='Client: ' +
                project['client'] +
                ' Hit ENTER to show menu, press ALT for more info.',
                modifier_subtitles={
                'alt': 'Tags: ' + ', '.join(taglist),
    },
        arg=str(project['id']),
        valid=True,
        icon='icons/project_{0}.png'.format(
                    project['project_state']).lower(),
        copytext=project['name'])


def build_taglist(tags):
    """Generate a list of tags."""
    taglist = []
    for tag in tags:
        taglist.append(tag['value'].lower())
    return taglist


def build_report_url(view, project):
    """Generate a string that contains the URL to a report."""
    from datetime import datetime
    now = datetime.now()
    report_title = 'Report: ' + project['name'] + ' - %s-%s-%s' % (now.day, now.month, now.year)
    client_id = get_client_data(project['client'])

    url = 'https://app.10000ft.com/report?filters=%7B%221%22%3A%22' + str(view) + '%22%2C%222%22%3A%2242%22%2C%2260%22%3A%7B%22mode%22%3A%22include%22%2C%22options%22%3A%5B%22project-' + str(project['id']) + '%22%5D%7D%2C%2280%22%3A%7B%22mode%22%3A%22include%22%2C%22options%22%3A%5B%22tag-' + str(client_id) + '%22%5D%7D%2C%22firstGroupBy%22%3A%22firstGroupByPhaseName%22%2C%22thenGroupBy%22%3A%22thenGroupByResource%22%2C%22customDateStart%22%3A%22' + str(project['starts_at']) + '%22%2C%22customDateEnd%22%3A%22' + str(project['ends_at']) + '%22%2C%22entryType%22%3A%7B%22mode%22%3A%22include%22%2C%22options%22%3A%5B%22entryTypeConfirmed%22%2C%22entryTypeFuture%22%5D%7D%7D&version=3'

    return url


def project_filter(filename):
    """Filter needed for deleting projects cache."""
    return 'projects' in filename


def update_data(update_method):
    """Update project data from 10.000ft"""
    wf.logger.debug('Starting update')
    cmd = ['/usr/bin/python', wf.workflowfile('update.py')]
    if update_method == 'force':
        cmd.append('--update')
        cmd.append('force')

    # Update projects data
    wf.logger.debug('Run update command : {}'.format(cmd))
    run_in_background('update', cmd)

    return 0


def update_project(project_id, action):
    """Update specific project in 10.000ft."""
    wf.logger.info('Started updating project')

    import json
    from lib import pycurl
    from StringIO import StringIO

    buffer = StringIO()
    project_deleted = None

    # Set access variables
    api_key = wf.get_password('10k_api_key')
    url = 'https://api.10000ft.com/api/v1/projects/' + \
        str(project_id) + '?auth=' + str(api_key)

    # Determine other variables based on the action
    if action == 'archive_project':
        data = json.dumps({"id": project_id, "archived": "true"})
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
    c.setopt(pycurl.POSTFIELDS, data)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    # Capture the response and store the json in a dictionary
    result = buffer.getvalue()
    wf.logger.info('Request is finished. Result from 10.000ft: ' + str(result))

    project = ''

    try:
        # Test if result is valid JSON
        project = json.loads(result)
    except ValueError, e:
        # When the project is deleted, 10.000ft responds with an empty string
        # (no JSON)
        project_deleted = True

    # Finishing up based on response from 10.000ft
    if project_deleted is True:
        # The project is deleted!
        wf.logger.info('The project with id ' + project_id +
                       ' is succesfully deleted from 10.000ft')
        notify_title = 'Your project is deleted!'
        notify_text = 'The project is succesfully deleted from 10.000ft'

        update_data('force')

    elif 'id' in project:
        # If we get an object with a project ID this means that the project
        # update of data was succesfull
        wf.logger.debug('Processed result to project: ' + str(project))
        # If everything goes well 10.000ft returns all the updated project info
        notify_title = 'Your project is updated!'
        notify_text = status + project['name']

        # Initiate force update
        update_data('force')

    elif 'message' in project:
        # 10.000ft returns a message if something went wrong
        notify_title = 'Something went wrong :-/'
        notify_text = project['message']
        wf.logger.info(
            'Something went wrong :-/.'
            ' Message from 10.000ft: ' + str(project['message']))

    else:
        notify_title = 'An error occured :-/)'
        notify_text = 'Check the log files for more information'

    return notify(notify_title, notify_text)

####################################################################
# Alfred Workflow Main
####################################################################


def main(wf):
    wf.logger.info('Started main')
    ####################################################################
    # Check for Update
    ####################################################################

    # Update available?
    # wf.logger.debug(wf.cached_data(__workflow_update_status))
    if wf.update_available:
        wf.add_item('A newer version is available',
                    'Press ENTER to install update',
                    autocomplete='workflow:update',
                    icon='update_available.png')

    ####################################################################
    # Get and Parse arguments
    ####################################################################

    # Build argument parser to parse script args and collect their values
    parser = argparse.ArgumentParser()

    # Keyword actions:
    # Save the API key
    parser.add_argument('--setkey', dest='apikey', nargs='?', default=None)
    # Save the tag for this user
    parser.add_argument('--setuser', dest='user', nargs='?', default=None)
    # Update data
    parser.add_argument('--update', dest='update_method',
                        nargs='?', default='normal')
    # Show only projects for a specific tag
    parser.add_argument('--user', dest='user_tag', nargs='?', default=None)

    # Show the list of options for the selected project
    parser.add_argument('--options', dest='project_id',
                        nargs='?', default=None)

    # Submenu options, project_id is stored in args.project_id
    parser.add_argument('--archive_project',
                        dest='project_id', nargs='?', default=None)
    parser.add_argument('--delete_project',
                        dest='project_id', nargs='?', default=None)

    # Add an optional query and save it to 'query'
    parser.add_argument('query', nargs='?', default=None)

    # Parse the script's arguments
    args = parser.parse_args(wf.args)

    ####################################################################
    # Run argument-specific actions
    ####################################################################

    # Save the API key
    if args.apikey:  # Script was passed an API key
        # Save the provided API key
        wf.save_password('10k_api_key', args.apikey)

        # Notify the user
        notify_title = 'Saved API key'
        notify_text = 'Your 10.000ft API key was saved'

        return notify(notify_title, notify_text)

    # Save the tag for this user
    if args.user:  # Script was passed a username
        # save the user
        wf.settings['user'] = args.user.lower()
        wf.logger.debug('WF settings: ' + str(wf.settings))

        # Notify the user
        notify_title = 'Saved User-tag-name'
        notify_text = 'Your 10.000ft User-tag-name was saved'

        return notify(notify_title, notify_text)

    # Update data
    if wf.args[0] == '--update':
        # Update data from 10.000ft
        update_method = args.update_method
        update_data(update_method)

        # Notify the user
        notify_title = 'Update running'
        notify_text = 'Data will be fetched from 10.000ft.'
        return notify(notify_title, notify_text)

    # Update project: Archive
    if wf.args[0] == '--archive_project':
        # Archive project if --archive_project
        update_project(args.project_id, 'archive_project')
        return 0

    # Update project: Delete
    if wf.args[0] == '--delete_project':
        # Delete project if --delete_project
        update_project(args.project_id, 'delete_project')
        return 0

    ####################################################################
    # Get data and filter 10.000ft projects
    ####################################################################

    # Is the API key stored in the Keychain?
    try:
        wf.get_password('10k_api_key')
    except PasswordNotFound:  # API key has not yet been set
        wf.add_item('No API key set.',
                    'Please use .10ksetkey to set your 10.000ft API key.',
                    valid=False,
                    icon='icons/warning.png')
        wf.send_feedback()
        return 0

    # Get query from Alfred
    query = args.query

    # Get posts from cache. Set `data_func` to None, as we don't want to
    # update the cache in this script and `max_age` to 0 because we want
    # the cached data regardless of age
    projects = wf.cached_data('projects', None, max_age=0)
    clients = wf.cached_data('clients', None, max_age=0)

    # Start update script if cached data is too old (or doesn't exist)
    if not wf.cached_data_fresh('projects', max_age=600):
        update_data('refresh')

    if not wf.cached_data_fresh('clients', max_age=600):
        update_data('refresh')

    # Notify the user if the cache is being updated
    if is_running('update'):
        wf.add_item('Fetching data from 10.000ft...',
                    valid=False,
                    icon='icons/fetching_data.png')

    # If script was passed a query, use it to filter projects
    if query and projects:
        projects = wf.filter(
            query, projects, key=search_key_for_project, min_score=20)

    # If we have no data to show, so show a warning and stop
    if not projects:
        wf.add_item('No projects found', icon='icons/warning.png')
        wf.send_feedback()
        return 0

    # TODO: is this efficient?
    if not clients:
        wf.add_item('No clients found', icon='icons/warning.png')
        wf.send_feedback()
        return 0

    ####################################################################
    # Show submenu options for project
    ####################################################################

    # If argument --options is passed on, show the options for manipulating a
    # project.
    if wf.args[0] == '--options':

        # Get current project data
        wf.logger.info('Started building options menu')
        project = get_project_data(args.project_id)

        # Build report URLs
        report_time = build_report_url(25, project)
        report_fees = build_report_url(27, project)

        # Add options for projects
        wf.add_item(title='View project',
                    arg='https://app.10000ft.com/viewproject?id=' +
                        str(project['id']),
                    valid=True,
                    icon='icons/project_view.png'
                    )
        wf.add_item(title='Edit project',
                    arg='https://app.10000ft.com/editproject?id=' +
                        str(project['id']),
                    valid=True,
                    icon='icons/project_edit.png'
                    )
        wf.add_item(title='Budget report time for project',
                    arg=report_time,
                    valid=True,
                    icon='icons/project_budget_report_time.png'
                    )
        wf.add_item(title='Budget report fees for project',
                    arg=report_fees,
                    valid=True,
                    icon='icons/project_budget_report_fees.png'
                    )
        wf.add_item(title='Archive project',
                    arg='10000ft.py --archive_project ' + str(project['id']),
                    valid=True,
                    icon='icons/project_archive.png'
                    )
        wf.add_item(title='Delete project',
                    arg='10000ft.py --delete_project ' + str(project['id']),
                    valid=True,
                    icon='icons/project_delete.png'
                    )
        # Send the results to Alfred as XML
        wf.send_feedback()

    ####################################################################
    # Show List of projects
    ####################################################################

    else:
        # Loop through the returned projects and add an item for each to the
        # list of results for Alfred
        for project in projects:
            # Extract tags from data and put them in a list
            taglist = build_taglist(project['tags']['data'])

            if wf.args[0] == '--user':
                # Only show projects of current user if the argument --user is
                # passed on
                if 'user' in wf.settings:
                    # Get the user tag from wf.settings
                    user_tag = wf.settings['user']
                    # Check if the current user_tag is in the list of tags for
                    # this project.
                    if user_tag in taglist:
                        # Add the project to the list as an item
                        add_project(project, taglist)
                else:
                    # Show an error if the 'user' key is not in wf.settings
                    wf.add_item('No User-tag-name saved.',
                                ('Please use .10ksetuser to set '
                                 'your 10.000ft User-tag-name.'),
                                valid=False,
                                icon='icons/warning.png')
                    wf.send_feedback()
                    return 0
            else:
                # In all other situations, just show the list of all the
                # projects
                add_project(project, taglist)
        # Send the results to Alfred as XML
        wf.send_feedback()
        return 0


if __name__ == '__main__':
    wf = Workflow(help_url=HELP_URL,
                  update_settings=UPDATE_SETTINGS)
    log = wf.logger
    sys.exit(wf.run(main))
