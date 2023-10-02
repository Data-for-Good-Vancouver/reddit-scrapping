import pandas as pd
import boto3

BUCKET = 'dataforgood-socials'

def get_subreddit_files(subreddit: str):
    s3 = boto3.client('s3')
    files = [file['Key'] for file in s3.list_objects_v2(
        Bucket=BUCKET,
        Prefix=subreddit if subreddit.endswith('/') else subreddit + '/'
    )['Contents']]
    files = list(filter(lambda file: file.endswith('.parquet'), files))
    return files

def get_subreddit_posts(subreddit: str) -> pd.DataFrame:
    files = get_subreddit_files(subreddit)
    data = pd.concat(
        (pd.read_parquet(f's3://{BUCKET}/{file}') for file in files)
    )
    return data.drop_duplicates(subset=['id'])