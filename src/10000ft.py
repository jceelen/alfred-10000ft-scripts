# encoding: utf-8
import sys
import json
import argparse
from workflow import Workflow, ICON_WEB, ICON_WARNING, web

def get_projects():
    f = open('./data/all_projects.json')
    r = f.read()

    # Parse the JSON returned by pinboard and extract the posts
    result = json.loads(r)
    projects = result['data']

    return projects

def search_key_for_project(project):
    """Generate a string search key for a post"""
    elements = []
    elements.append(project['name'])  # projectnaam
    elements.append(project['client'])  # klant
    elements.append(str(project['project_code']))  # projectcode
    return u' '.join(elements)

def main(wf):
    # Get query from Alfred
    if len(wf.args):
        query = wf.args[0]
    else:
        query = None

    # Retrieve posts from cache if available and no more than 60
    # seconds old
    projects = get_projects() #wf.cached_data('projects', get_projects, max_age=600)    

    # If script was passed a query, use it to filter posts
    if query:
        projects = wf.filter(query, projects, key=search_key_for_project, min_score=20)
    
    # Loop through the returned posts and add an item for each to
    # the list of results for Alfred
    for project in projects:
        wf.add_item(title=project['name'],
                    subtitle=project['client'],
                    arg=str(project['id']),
                    valid=True,
                    icon=ICON_WEB)
    
    # Send the results to Alfred as XML
    wf.send_feedback()

if __name__ == u"__main__":
    wf = Workflow()
    sys.exit(wf.run(main))
