import pandas as pd
import boto3

BUCKET = 'dataforgood-socials'

def get_subreddit_files(subreddit: str):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(
        Bucket=BUCKET, 
        Prefix=subreddit if subreddit.endswith('/') else subreddit + '/'
    )
    files = []
    for page in pages:
        for obj in page['Contents']:
            files.append(obj['Key'])
    files = list(filter(lambda file: file.endswith('.parquet'), files))
    return files

def get_subreddit_posts(subreddit: str) -> pd.DataFrame:
    files = get_subreddit_files(subreddit)
    data = pd.concat(
        (pd.read_parquet(f's3://{BUCKET}/{file}') for file in files)
    )
    return data.drop_duplicates(subset=['id'])