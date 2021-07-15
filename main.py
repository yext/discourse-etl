from logging import error
import os
import requests
import json
import time
import argparse
from urllib.parse import urljoin
from yext import YextClient
from yext.exceptions import YextException
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import track
from typing import List, Dict
from mapping import transform_profile, topic_mappings

load_dotenv()

MAX_PAGES = 1000
YEXT_API_KEY = os.getenv('YEXT_API_KEY')
DISCOURSE_API_KEY = os.getenv('DISCOURSE_API_KEY')
DISCOURSE_BASE_URL = 'https://hitchhikers.yext.com/community/'
DISCOURSE_URL = 'https://hitchhikers.yext.com/community/latest.json'
DISCOURSE_TOPIC_URL = 'https://hitchhikers.yext.com/community/t/{id}.json'

console = Console()
yext_client = YextClient(YEXT_API_KEY)

def get_all_topics(discourse_url: str, discourse_api_key: str) -> List:
    '''
    Fetch all the topics from a Discourse URL. Handles pagination.
    Returns a list of all the topics.
    '''
    auth = requests.auth.HTTPBasicAuth('Api-Key', discourse_api_key)
    page = 0
    response = requests.get(discourse_url, auth=auth, params={'page': page})
    rj = response.json()
    all_topics = []
    with console.status("Beginning pagination...", spinner="monkey") as status:
        while ('more_topics_url' in rj['topic_list']) and (page < MAX_PAGES):
            response.raise_for_status()
            page_topics = rj['topic_list']['topics']
            all_topics.extend(page_topics)
            page += 1
            response = requests.get(discourse_url, auth=auth, 
                                    params={'page': page})
            rj = response.json()
            status.update(f'Paginated through {page} pages.')
    return all_topics


def get_topic_data(topic_id: int, error_timeout: float = 4, 
                   retries_remaining: int = 3) -> Dict:
    '''
    Fetches the topic data for a single Discourse topic (i.e. community post)
    '''
    topic_url = DISCOURSE_TOPIC_URL.format(id=str(topic_id))
    auth = requests.auth.HTTPBasicAuth('Api-Key', DISCOURSE_API_KEY)
    response = requests.get(topic_url, auth=auth)
    if response.status_code == 500:
        if retries_remaining:
            msg = f'Encountered error on topic: {topic_id}. Retrying.'
            console.log(msg, style='bold red')
            time.sleep(error_timeout)
            get_topic_data(topic_id, error_timeout, retries_remaining-1)
        else:
            response.raise_for_status()
    response.raise_for_status()
    return response.json()


def main(args):
    timeout = args.timeout
    error_timeout = args.error_timeout
    retries = args.retries
    all_topics = get_all_topics(DISCOURSE_URL, DISCOURSE_API_KEY)
    all_topic_data = []
    for topic in track(all_topics, description='Fetching topic data...'):
        topic_id = topic['id']
        try:
            topic_data = get_topic_data(topic_id, error_timeout, retries)
        except requests.exceptions.HTTPError:
            #TODO: Add better, configurable error handling.
            console.log(f'Failed to fetch topic: {topic_id}. Proceeding.')
            continue
        all_topic_data.append(topic_data)
        time.sleep(timeout)
    transformed_topics = []
    for topic in track(all_topic_data, description='Uploading topic data...'):
        topic_id = str(topic['id'])
        base_profile = {
            'meta': {
                'id': topic_id,
                'countryCode': 'US',
                'labels': ["135779"]
            }
        }
        transformed_topic = transform_profile(topic, topic_mappings, base_profile)
        try:
            yext_client.upsert_entity(
                id=topic_id, #TODO Update SDK so it doesn't require redundancy. 
                profile=transformed_topic, 
                entity_type='ce_discoursePost',
                format='html',
                strip_unsupported_formats=True
            )
        except YextException as e:
            #TODO Add better, configurable error handling.
            console.log(e)
            console.log(transformed_topic)
        time.sleep(timeout)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=float, default=0.75,
                        help='Timeout between each fetch request.')
    parser.add_argument('--error_timeout', type=float, default=5, 
                        help='Elongated timeout for 500 errors.')
    parser.add_argument('--retries', type=int, default=3, 
                        help='Number of times to retry after 500.')
    args = parser.parse_args()
    main(args)