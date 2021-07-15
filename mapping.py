import re
import json
from urllib.parse import urljoin
from jsonpath_ng import jsonpath, parse

def fix_relative_urls(text: str, base_url: str):
    '''
    Makes relative URLs into absolute ones because KG doesn't accept relative.
    '''
    relative_pattern = r'href="(\/[\w/]+)"'     
    cleaned_str = re.sub(
        relative_pattern, 
        lambda relative: f'href="{urljoin(base_url, relative.group(1))}"',
        text
    )
    return cleaned_str


def fix_avatar_template(avatar_url, base_url):
    '''
    Interpolates a size of 20 to the avatar template and fixes relative URLs.
    '''
    avatar_url = avatar_url.format(size='20')
    if not avatar_url.startswith('https'):
        avatar_url = urljoin(base_url, avatar_url)
    return avatar_url


def transform_profile(raw_profile, mappings, base_profile=None):
    '''Transform a raw JSON profile into Knowledge Graph JSON via mappings.'''
    transformed_profile = base_profile if base_profile else {}
    for field, mapper in mappings.items():
        mappers = [mapper] if isinstance(mapper, dict) else mapper
        for mapper in mappers:
            kg_field = mapper['kgField']
            transformer = mapper.get('transform', lambda x: x)
            optional = mapper.get('optional', False)
            jsonpath_expr = parse(field)
            raw_field = [match.value for match in jsonpath_expr.find(raw_profile)]
            if not raw_field:
                if not optional:
                    raise ValueError(f'Could not find matches for this path: {field}')
                else:
                    continue
            else: 
                raw_field = raw_field[0]
            transformed_value = transformer(raw_field)
            transformed_profile[kg_field] = transformed_value
    return transformed_profile


post_mapping = {
    'cooked': {
        'kgField': 'text',
        'transform': lambda x: fix_relative_urls(x, 'https://hitchhikers.yext.com/')
    },
    'name': {
        'kgField': 'authorName'
    },
    'username': {
        'kgField': 'authorUsername'
    },
    'id': {
        'kgField': 'postID',
        'transform': lambda x: str(x)
    },
    'avatar_template': {
        'kgField': 'avatarTemplate'
    }
}

poster_mapping = {
    'id': {
        'kgField': 'iD',
        'transform': lambda x: str(x)
    },
    'name': {
        'kgField': 'name',
    },
    'avatar_template': {
        'kgField': 'avatarTemplate',
        'transform': lambda template: {
            'url': fix_avatar_template(template, 'https://hitchhikers.yext.com/'),
            'alternateText': 'Null'
        }
    }
}

topic_mappings = {
    'post_stream.posts': {
        'kgField': 'c_discoursePosts',
        'transform': lambda posts: [transform_profile(post, post_mapping) for post in posts]
    },
    'post_stream.posts[0]': {
        'kgField': 'c_firstDiscoursePost',
        'transform': lambda post: transform_profile(post, post_mapping)
    },
    'title': {
        'kgField': 'name'
    },
    'fancy_title': {
        'kgField': 'c_discourseFancyTitle'
    },
    'slug': {
        'kgField': 'c_discourseSlug'
    },
    'details.participants': {
        'kgField': 'c_posters',
        'transform': lambda posters: [transform_profile(poster, poster_mapping) for poster in posters] 
    },
    'created_at': {
        'kgField': 'c_createdAt',
        'transform': lambda date: date[:10]
    },
    'last_posted_at': {
        'kgField': 'c_lastPostedDate',
        'transform': lambda date: date[:10]
    },
    'views': {
        'kgField': 'c_postViews',
        'transform': str
    },
    'like_count': {
        'kgField': 'c_postLikes',
        'transform': str
    },
    'reply_count': {
        'kgField': 'c_replyCount',
        'transform': str
    },
    'has_deleted': {
        'kgField': 'c_postDeleted',
        'transform': lambda deleted: 'Yes' if deleted else 'No',
        'optional': True
    },
    'category_id': {
        'kgField': 'c_postCategory',
        'transform': str
    }
}