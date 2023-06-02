import sys
import os
from datetime import datetime

import boto3
import praw
from reddit_worker import SubRedditWorker, S3Exporter

def update_event_schedule(subreddit: str, arn: str):
    name=f'DFG-reddit-{subreddit}'
    group = 'DFG-socials'
    scheduler_client = boto3.client('schedule')

    scheduler = scheduler_client.get_schedule(GroupName=group, Name=name)
    target = scheduler['Target'][0]

    
    scheduler_client.update_schedule(
        Name=name,
        schedule_expression=f'rate(1 minute)',
        Target=target
    )

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
    posts = worker._get_lasts_submissions()
    posts = posts[posts['created_utc']>last_run]
    if len(posts)>0:
        worker.exporter.export(posts)
    return len(posts)

def handler(event, context):
    return 'Hello from AWS Lambda using Python' + sys.version + '! update 1'      
    print(context.invoked_function_arn)
    subreddit = event['subreddit']
    last_run = event['last_run']

    print(context.invoked_function_arn)
    print(context.function_name)
    arn = context.invoked_function_arn

    posts_updated: int = save_new_data(subreddit, last_run)
    needs_update = posts_updated>200 or posts_updated<800
    
    if posts_updated<200:
        needs_update = True
        schedule_expression=f'rate(1 minute)'
        
    elif posts_updated>800:
        needs_update = True
        schedule_expression=f'rate(1 minute)'
    #TODO update last run

    if needs_update:
        update_event_schedule(subreddit, arn)
    return f'{posts_updated} were saved'