import os
import praw
import datetime as dt
from functools import cached_property
from dataclasses import dataclass
from typing import Optional, Protocol
from time import sleep
import boto3

import pandas as pd


class RedditsExporter(Protocol):
    def export(self, df: pd.DataFrame) -> None:
        ...


class IncrementalCSVExporter:
    def __init__(self, path: str) -> None:
        self.path = path

    def export(self, df: pd.DataFrame) -> None:
        if os.path.exists(self.path):
            df.to_csv(
                self.path,
                mode='a',
                header=False,
                index=False
            )
        else:
            df.to_csv(self.path)

class S3Exporter():
    def __init__(self, base_path: str) -> None:
        self.base_path = base_path

    def export(self, df: pd.DataFrame) -> None:
        df.to_parquet(f'{self.base_path}/{dt.datetime.now().strftime("%Y-%m-%dT%H:%M")}.parquet', index=False)

COLUMNS = [  # TODO use this as default but allow to pass it as parameter
    'title', 'score', 'id', 'name', 'url',
    'author', 'selftext', 'approved_at_utc', 'banned_at_utc', 'created_utc'
]


@dataclass
class SubRedditWorker:
    subreddit: str
    reddit_instance: praw.Reddit
    exporter: RedditsExporter
    starting_interval: int = 6000  # 10 minutes
    interval_step: int = 60
    submissions_amount: int = 1000

    def __post_init__(self) -> None:
        self.subreddit_instance = self.reddit_instance.subreddit(
            self.subreddit)

    def _get_lasts_submissions(self) -> pd.DataFrame:
        posts = []
        for submission in self.subreddit_instance.new(limit=1_000):
            posts.append(
                (
                    submission.title,
                    submission.score,  # upvotes
                    submission.id,
                    submission.name,
                    submission.url,
                    submission.author.name if submission.author else None,
                    submission.selftext,
                    submission.approved_at_utc,
                    submission.banned_at_utc,
                    submission.created_utc,
                )
            )
        df = pd.DataFrame(
            posts,
            columns=COLUMNS
        )
        df['created_utc'] = df['created_utc'].map(dt.datetime.fromtimestamp)
        return df
    
    def run_once(self) -> None:
        submissions = self._get_lasts_submissions()
        self.exporter.export(submissions)

async def run_forever(reddit_worker) -> None:
    interval = reddit_worker.starting_interval
    last_post = None
    while True:
        submissions = reddit_worker._get_lasts_submissions()
        if last_post is not None:
            submissions = submissions[
                submissions['created_utc'] > last_post['created_utc']
            ]
        reddit_worker.exporter.export(submissions)

        if len(submissions) == 1000:
            interval -= reddit_worker.interval_step
            interval = 1 if interval < 1 else interval
        elif submissions.empty:
            interval += reddit_worker.interval_step

        last_post = submissions.iloc[0] if not submissions.empty else last_post
        print(f'{interval=}')
        sleep(interval)

