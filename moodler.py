#!/usr/bin/env python3

import sys, os
from colorama import Fore
import requests
from urllib import parse
import bs4
import re

# scrapes resource files from Moodle
# author: rob

USAGE = """
python moodler.py -h host -t token -c <course_id> [-s <section_id>]
-h <host>       The host to connect to.
-t <token>      The Moodle session token. Prefix with @ to read from a file.
-c <course_id>  The ID of the course to scrape.
-s <section_id> The ID of the section to scrape.
                Optional: if only a course ID is provided,
                will attempt to find and scrape all sections.
"""

host = None
token = None
courseId = None
sectionId = None

def fail(msg: str, print_usage=False):
    print(f'{Fore.RED}{msg}{Fore.RESET}')
    if print_usage:
        print(USAGE)
    exit()

i = 0

def eat_arg() -> str | None:
    global i
    if (i+1) >= len(sys.argv):
        return None
    return sys.argv[(i:=i+1)]

def eat_value_for(switch) -> str:
    arg = eat_arg()
    if not arg:
        raise Exception(f'Missing value for {switch}.')
    return arg

try:
    while (arg := eat_arg()):
        match arg:
            case '--help' | '-?' | '/help' | '/?':
                print(USAGE)
                exit()
            case '-h': # host
                host = eat_value_for(arg)
            case '-t': # Moodle token
                token = eat_value_for(arg)
            case '-c': # course
                courseId = eat_value_for(arg)
                if not str.isdigit(courseId):
                    fail('Course ID must be a number.')
                courseId = int(courseId)
                if courseId < 0:
                    fail('Course ID must not be negative.')
            case '-s': # section
                sectionId = eat_value_for(arg)
                if not str.isdigit(sectionId):
                    fail('Section ID must be a number.')
                sectionId = int(sectionId)
                if sectionId < 0:
                    fail('Section ID must not be negative.')
            case unknown:
                raise Exception(f'Unknown argument: {unknown}.')
except Exception as e:
    fail(str(e), True)

if not host:
    fail('A host must be provided.', True)

if not token:
    fail('Session token must be provided.', True)

if token.startswith('@'):
    try:
        tokenFile = token[1:]
        if not os.path.exists(tokenFile):
            fail(f'Session token file does not exist.')
        with open(token[1:], 'r') as f:
            token = f.read()
    except Exception as ex:
        fail(f'Failed to read session token file: {ex}')

token = token.strip()
if len(token) == 0:
    fail('Provided session token is empty.')

if not courseId:
    fail(f'A course ID must be provided.', True)

def scrape_course(course_id, host, token):
    cookies = { 'MoodleSession': token }
    url = f'https://{host}/course/view.php?id={course_id}'
    print(f'Fetching course {course_id} ... ', end='', flush=True)
    res = requests.get(url, cookies=cookies)
    if res.status_code != 200:
        raise Exception(f'{res.status_code} {res.reason}')

    soup = bs4.BeautifulSoup(res.content, features='html.parser')
    if soup.find(text='Enrolment options'):
        raise Exception('not enrolled or not authorized')
    
    rgxCourseSection = re.compile(
        f'^.*course/view\\.php\\?id={course_id}&section=(\\d+)$'
    )
    links = soup.find_all('a', href=rgxCourseSection)
    if len(links) == 0:
        print(f'{Fore.YELLOW}no sections found{Fore.RESET}')
        return

    sectionIds = set()
    for link in links:
        match = rgxCourseSection.match(link.attrs['href'])
        if not match: continue
        sectionIds.add(int(match[1]))
    
    if len(sectionIds) == 0:
        print(f'{Fore.YELLOW}no sections found{Fore.RESET}')
        return
    
    print(f'{Fore.GREEN}OK{Fore.RESET}', flush=True)

    for sectionId in sorted(sectionIds):
        scrape_section(course_id, sectionId, host, token)

def scrape_section(course_id, section_id, host, token):
    cookies = { 'MoodleSession': token }
    url = f'https://{host}/course/view.php?id={course_id}&section={section_id}'
    print(f'Fetching course {course_id} section {section_id} ... ', end='', flush=True)
    res = requests.get(url, cookies=cookies)
    if res.status_code != 200:
        raise Exception(f'{res.status_code} {res.reason}')
    soup = bs4.BeautifulSoup(res.content, features='html.parser')
    if soup.find(text='Enrolment options'):
        raise Exception('not enrolled or not authorized')
    
    links = soup.select('.single-section .activity.resource a')
    if len(links) == 0:
        print(f'{Fore.YELLOW}no resource links found{Fore.RESET}')
        return
    
    print(f'{Fore.GREEN}OK{Fore.RESET}')
    
    basePath = f'courses/{course_id}/{section_id}'
    os.makedirs(basePath, exist_ok=True)

    for link in links:
        name = link.get_text()
        instancename = link.select_one('.instancename')
        if instancename:
            name = ''.join(instancename.find_all(text=True, recursive=False))
        print(f'Downloading "{name}" ... ', end='', flush=True)
        res = requests.get(link.attrs["href"], allow_redirects=False, cookies=cookies)
        if res.status_code // 100 != 3:
            print(f'{Fore.YELLOW}no redirect ({res.status_code} {res.reason}){Fore.RESET}')
            continue
        fileUrl = res.headers['Location']
        if not fileUrl:
            print(f'{Fore.RED}failed to find location{Fore.RESET}')
            continue
        
        fileName = parse.unquote(fileUrl.split('/')[-1])
        if '?' in fileName:
            fileName = fileName.split('?')[0]
        filePath = os.path.join(basePath, fileName)

        print(f'{fileName} ... ', end='', flush=True)
        if os.path.exists(filePath):
            print(f'{Fore.YELLOW}already exists{Fore.RESET}')
            continue
        
        res = requests.get(fileUrl, cookies=cookies)
        if res.status_code != 200:
            print(f'{Fore.RED}get request failed. ({res.status_code} {res.reason}){Fore.RESET}')
            continue
        with open(filePath, 'wb') as f:
            f.write(res.content)
        print(f'{Fore.GREEN}done{Fore.RESET}')

try:
    if not sectionId:
        scrape_course(courseId, host, token)
    else:
        scrape_section(courseId, sectionId, host, token)
except Exception as e:
    fail(str(e))