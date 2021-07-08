import os
import traceback
from dotenv import load_dotenv
from rich.console import Console
from flask import Flask, request
from yext import YextClient
from yext.exceptions import YextException
from mapping import transform_profile, topic_mappings
from main import get_topic_data


app = Flask(__name__)
console = Console()
load_dotenv()

YEXT_API_KEY = os.getenv('YEXT_API_KEY')
yext_client = YextClient(YEXT_API_KEY)

@app.route('/discourse', methods=['POST'])
def discourse():
    '''
    Function for handling messages from the Discourse webhook.
    If we receive a update on a post, then we fetch the post and upsert it.
    If we receive an update on a topic directly, we just upsert the topic.
    '''
    response = {}
    body = request.json
    console.log(body)
    if 'post' in body:
        post = body['post']
        topic_id = post['topic_id']
    elif 'topic' in body:
        topic_id = body['topic']['id']
    topic = get_topic_data(topic_id)
    console.log(topic)
    base_profile = {
        'meta': {
            'id': str(topic_id),
            'countryCode': 'US',
            'labels': ["135779"]
        }
    }
    transformed_topic = transform_profile(topic, topic_mappings, base_profile)
    try:
        yext_response = yext_client.upsert_entity(
            id=topic_id,
            profile=transformed_topic, 
            entity_type='ce_discoursePost',
            format='html',
            strip_unsupported_formats=True
        )
        response['status'] = 'Success'
        response['yextResponse'] = yext_response
        return response, 200
    except YextException as e:
        response['status'] = 'Failure'
        response['traceback'] = traceback.print_exc()
        return response, 400
    return {'status': 'Unknown Failure'}, 400

if __name__ == '__main__':
    app.run(port=8000, debug=True)