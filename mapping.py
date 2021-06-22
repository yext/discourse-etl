import json
from jsonpath_ng import jsonpath, parse


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
                    console.log(raw_profile)
                    # console.log(raw_field)
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
        'kgField': 'text'
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
    }
}