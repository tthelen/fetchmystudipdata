# Description: Fetch data from the Stud.IP JSON API.
# Author: Tobias Thelen
# Date: 2025-11-27
# License: Public Domain
import json, os

import requests

# never put valuable credentials in your code
# local_settings is excluded from git by .gitignore
from local_settings import username, password

# Documentation: https://docs.gitlab.studip.de/entwicklung/docs/jsonapi
base_url = 'https://studip.uni-osnabrueck.de'
api_url = base_url+'/jsonapi.php/v1'

def fetch(url, offset=0, limit=10, noparams=False, verbose=False):
    """Fetch a URL and return the JSON response.

    :param url: The URL to fetch.
    :param offset: The offset for pagination.
    :param limit: The limit for pagination.
    :param noparams: If True, don't add pagination parameters (some routes don't support pagination).
    :param verbose: If True, print the URL before fetching.
    :return: The JSON response as a dictionary.
    """
    url = f"{api_url}{url}"
    if not noparams:
        url = url + f"?page[offset]={offset}&page[limit]={limit}"
    if verbose:
        print("Fetching", url)
    response_data = requests.get(url, auth=(username, password))
    if response_data.status_code != 200:
        # print(f"Error fetching {url}: {response_data.status_code}")
        return {}
    if verbose:
        print("Response:", response_data.text)
    return response_data.json()


def fetch_me():
    """Fetch the user data from the API and return it as a dictionary."""

    route = f"/users/me"
    return fetch(route, noparams=True)['data']


def download_file(id, semester_name, course_name, studip_path, filename):
    """Download a file from a URL and save it to the disk.

    :param: url: The URL to download the file from.
    :param: semester_name: The name of the semester.
    :param: course_name: The name of the course.
    :param: studip_path: The path of the file in the Stud.IP course.
    :param: filename: The name of the file.
    :returns: None

    Folder structure on disk is:
    semester_name/course_name/studip_course_path/filename
    """

    global base_url, username, password

    # replace illegal characters for filenames in semester_name and course_name
    semester_name = semester_name.replace('/', '_')
    course_name = course_name.replace('/', '_')

    # create the folder structure
    path = f'data/{semester_name}/{course_name}/{studip_path}'
    os.makedirs(path, exist_ok=True)

    # download the file
    response = requests.get(api_url+'/file-refs/'+id+'/content', auth=(username, password))
    with open(f'{path}/{filename}', 'wb') as f:
        f.write(response.content)


def fetch_files(id, semester, course, path='', folder_id=None, folder_name=None):

    if not folder_id:  # we are in the root folder
        folder_id = fetch_root_folder(id)
        folder_name = ''
        if not folder_id:
            return

    # for the current folder_id:
    # 1. Fetch and download all files
    route = f"/folders/{folder_id}/file-refs"
    response = fetch(route, limit=1000, verbose=False)
    if response:  # we have files
        for f in response['data']:
            if folder_name:
                if path:
                    path = path + '/' + folder_name
                else:
                    path = folder_name
            download_file(f['id'], semester, course, path, f['attributes']['name'])

    # 2. Fetch all subfolders and call fetch_files recursively
    route = f"/folders/{folder_id}/folders"
    response = fetch(route, limit=1000, verbose=False)
    if response:  # no files or access forbidden
        for f in response['data']:
            fetch_files(id, semester, course, path+f['attributes']['name']+'/', f['id'])



def fetch_root_folder(id):
    route = f"/courses/{id}/folders"
    resp = fetch(route, verbose=False)
    if 'data' in resp:
        for folder in resp['data']:
            if folder['attributes']['folder-type'] == 'RootFolder':
                return folder['id']
    return None

def fetch_course(id):
    """Fetch a course from the API and return it as a dictionary."""
    route = f"/courses/{id}"
    return fetch(route, noparams=True)['data']


def fetch_my_courses(user_id, limit=500):
    """Fetch all courses the user is registered for from the API and return them as a dictionary."""
    route = f"/users/{user_id}/course-memberships"
    memberships = fetch(route, limit=limit)['data']
    courses = []
    for membership in memberships:
        course_id = membership['relationships']['course']['data']['id']
        course = fetch_course(course_id)
        courses.append(course)

    return courses


def fetch_semesters():
    """Fetch all semesters from the API and return them as a dictionary.
    The dictionary is of the form
       {id: {name: 'name',
             start: 'start',  # ISO 8601 date
             end: 'end',  #
             start-of-lectures: 'start-of-lectures',  # ISO 8601 date
             end-of-lectures: 'end-of-lectures',  # ISO 8601 date
             visible: True/False,
             is_current: True/False}}

    To parse the dates in Python datetime objects, use this:

        from datetime import datetime

        date_string = "2002-10-14T00:00:00+02:00"
        parsed_date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")

    """
    route = f"/semesters"
    response = fetch(route, limit=100)
    semesters = {}
    for semester in response['data']:
        semesters[semester['id']] = semester['attributes']
    return semesters


# fetch the user data
me = fetch_me()
my_id = me['id']
print(f"Meine user_id: {my_id}")

# fetch all courses the user is registered for
courses = fetch_my_courses(my_id)
semesters = fetch_semesters()

# print(json.dumps(courses, indent=2))
for course in courses:
    semester_name = semesters[course['relationships']['start-semester']['data']['id']]['title']
    print(semester_name+': '+course['attributes']['title'])
    # print(course['attributes']['description'])
    files = fetch_files(course['id'], semester_name, course['attributes']['title'])


