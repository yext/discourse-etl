import os
import requests
import json
from urllib.parse import urljoin
from yext import YextClient
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import track
from typing import List, Dict
from mapping import transform_profile, topic_mappings

load_dotenv()

MAX_PAGES = 1
YEXT_API_KEY = os.getenv('YEXT_API_KEY')
DISCOURSE_API_KEY = os.getenv('DISCOURSE_API_KEY')
DISCOURSE_BASE_URL = 'https://hitchhikers.yext.com/community/'
DISCOURSE_URL = 'https://hitchhikers.yext.com/community/latest.json'
DISCOURSE_TOPIC_URL = 'https://hitchhikers.yext.com/community/t/{id}.json'

console = Console()
yext_client = YextClient(YEXT_API_KEY)
console.log(YEXT_API_KEY)


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
            response = requests.get(discourse_url, auth=auth, params={'page': page})
            rj = response.json()
            status.update(f'Paginated through {page} pages.')
    return all_topics


def get_topic_data(topic_id: int) -> Dict:
    '''
    Fetches the topic data for a single Discourse topic (i.e. community post)
    '''
    topic_url = DISCOURSE_TOPIC_URL.format(id=str(topic_id))
    auth = requests.auth.HTTPBasicAuth('Api-Key', DISCOURSE_API_KEY)
    response = requests.get(topic_url, auth=auth)
    return response.json()


def main():
    all_topics = get_all_topics(DISCOURSE_URL, DISCOURSE_API_KEY)
    all_topic_data = []
    for topic in track(all_topics, description='Fetching topic data...'):
        topic_id = topic['id']
        topic_data = get_topic_data(topic_id)
        all_topic_data.append(topic_data)
    transformed_topics = []
    for topic in track(all_topic_data, description='Uploading topic data...'):
        topic_id = str(topic['id'])
        base_profile = {
            'meta': {
                'id': topic_id,
                'countryCode': 'US',
                'labels': ["134088"]
            }
        }
        transformed_topic = transform_profile(topic, topic_mappings, base_profile)
        yext_client.upsert_entity(
            id=topic_id, #TODO - Update SDK so it doesn't require redundancy. 
            profile=transformed_topic, 
            entity_type='helpArticle',
            format='html',
            strip_unsupported_formats=True
        )

if __name__ == '__main__':
    main()