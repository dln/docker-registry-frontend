import html
import json
import os
import re

from dogpile.cache import make_region
from flask import g, render_template
from requests import RequestException

MAX_REPOSITORIES = 1000

region = make_region().configure(
    'dogpile.cache.memory_pickle'
)


def get_all_repositories():
    response = registry_request('_catalog?n={}'.format(MAX_REPOSITORIES))
    data = response.json()
    return data['repositories']


def process_manifest_data(data):
    hightlights = [
        r'^(FROM)', r'^(MAINTAINER)', r'^(RUN)', r'^(ADD)',
        r'^(COPY)', r'^(EXPOSE)', r'^(USER)', r'^(ENTRYPOINT)',
        r'^(CMD)', r'^(ENV)', r'^(VOLUME)', r'^(LABEL)', r'^(ARG)'
    ]

    replacements = {
        '/bin/sh -c #(nop) ': '',
        '/bin/sh -c ': 'CMD ',
        '/bin/sh': '',
        '-c': '',
        '#(nop)': ''
    }

    def process_cmds(cmds):
        if not cmds:
            raise StopIteration()
        for cmd in cmds:
            cmd = html.escape(cmd)
            for key in replacements:
                cmd = cmd.replace(key, replacements[key]).strip()
            for highlight in hightlights:
                cmd = re.sub(highlight, r'<span class="highlight">\1</span>', cmd)
            if cmd:
                yield cmd

    history = []
    tag_detail = {}
    if data.get('history'):
        for item in data.get('history', []):
            if item.get('v1Compatibility'):
                raw = json.loads(item['v1Compatibility'])
                if not tag_detail:
                    tag_detail = raw
                cmds = raw.get('container_config', {}).get('Cmd', '')
                history.extend(process_cmds(cmds))

    return history, tag_detail


def registry_request(path, method="GET"):
    api_url = os.environ['REGISTRY_URL'] + '/v2/' + path

    try:
        response = getattr(g.session, method.lower())(api_url, verify=g.config.get('registry_verify_ssl'))
        if response.status_code == 401:
            update_token(response.headers['Www-Authenticate'])
            response = getattr(g.session, method.lower())(api_url, verify=g.config.get('registry_verify_ssl'))
        return response
    except RequestException:
        raise Exception("Problem during docker registry connection")

def update_token(header):
    realm = find_between(header, 'realm="', '"')
    service = find_between(header, 'service="', '"')
    scope = find_between(header, 'scope="', '"')
    data = {"scope": scope, "service": service, "account": os.environ['REGISTRY_USER']}
    r = g.session.post(realm, data=data, auth=(os.environ['REGISTRY_USER'], os.environ['REGISTRY_PW']), verify=g.config.get('registry_verify_ssl'))
    data = r.json()
    g.session.headers.update({'Authorization':'Bearer ' + data['token']})

def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""

def frontend_template(template, **kwargs):
    '''
    Wrapper function around the flask render_template function
    to always set the frontend_url for the view.
    '''
    return render_template(template, frontend_url=g.config.get('frontend_url'), **kwargs)
