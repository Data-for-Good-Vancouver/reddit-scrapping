import os
import re
import json
import time
from datetime import datetime

import boto3
import pandas as pd
import praw
from botocore.config import Config

from link_description import get_meta_description
from reddit_worker import SubRedditWorker, S3Exporter


MINUTES_DELTA = 10
AWS_CONFIG = Config(
    region_name='us-east-1',
    retries={
        'max_attempts': 10,
        'mode': 'standard'
    }
)


def update_event_schedule(posts_updated: int, events_client, rule):
    needs_update = posts_updated > 200 or posts_updated < 800
    if not needs_update:
        return

    schedule_expression = rule['ScheduleExpression']
    minutes_search = re.search(
            r'rate\((\d+) minutes\)',
            schedule_expression
        )
    if minutes_search:
        minutes = int(minutes_search.group(1))
    else:
        raise ValueError('The schedule expression is not minutes.')
    minutes = 1440 if minutes > 1440 else minutes
    minutes = 10 if minutes < 10 else minutes

    if posts_updated < 200 and minutes < 1440:  # max 24 hours span
        minutes += MINUTES_DELTA
    elif posts_updated > 800 and minutes > 10:  # min 10 minuets
        minutes -= MINUTES_DELTA
    schedule_expression = f'rate({minutes} minutes)'

    events_client.put_rule(
        Name=rule['Name'],
        ScheduleExpression=schedule_expression,
        State='ENABLED',
        Description=rule.get('Description', ''),
        EventBusName=rule['EventBusName']
    )


def update_rule_target(event, events_client, rule):
    event['last_run'] = time.strftime('%Y-%m-%dT%H:%M:00')
    target = events_client.list_targets_by_rule(
        Rule=rule['Name'],
        EventBusName='default'
    )['Targets'][0]

    put_target_resp = events_client.put_targets(
        Rule=rule['Name'],
        Targets=[{
            'Id': target['Id'],
            'Arn': target['Arn'],
            'Input': json.dumps(event),
        }]
    )
    return put_target_resp


def save_new_data(subreddit: str, last_run: datetime) -> int:

    reddit = praw.Reddit(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        username=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        user_agent=f"DataForGoodTest"
    )

    worker = SubRedditWorker(
        subreddit=subreddit,
        reddit_instance=reddit,
        exporter=S3Exporter(f's3://dataforgood-socials/{subreddit}')
    )
    posts: pd.DataFrame = worker._get_lasts_submissions()
    posts['self_text'] = posts.apply(
        lambda row: row['self_text'] if pd.notna(row['selftext']) else get_meta_description(row['url']),
        axis=1
    )
    if last_run:
        posts = posts[posts['created_utc'] > last_run]
    if len(posts) > 0:
        worker.exporter.export(posts)
    return len(posts)


def handler(event, context):
    # params
    subreddit: str = event['subreddit']
    last_run: datetime = event['last_run']

    # rule data
    rule_name = f'DFG-reddit-{subreddit}'
    events_client = boto3.client(
        'events',
        config=AWS_CONFIG
    )
    rule = events_client.list_rules(
        NamePrefix=rule_name,
        EventBusName='default',
        Limit=1
    )['Rules'][0]

    #get and save new posts
    posts_updated: int = save_new_data(subreddit, last_run)

    # update event
    update_event_schedule(posts_updated, events_client, rule)
    update_rule_target(event, events_client, rule)

    return f'{posts_updated} were saved'
