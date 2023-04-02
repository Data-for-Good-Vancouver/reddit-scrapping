import os
import praw
import datetime as dt
from functools import cached_property
from dataclasses import dataclass
from typing import Optional, Protocol
from time import sleep

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
                header=False
            )
        else:
            df.to_csv(self.path)


COLUMNS = [  # TODO use this as default but allow to pass it as parameter
    'title', 'score', 'id', 'name', 'url',
    'author', 'selftext', 'approved_at_utc', 'banned_at_utc', 'created_utc'
]


@dataclass
class SubRedditWorker:
    subreddit: str
    reddit_instance: praw.Reddit
    exporter: RedditsExporter
    starting_interval: int = 300  # 5 minutes
    interval_step: int = 30
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
                    submission.author,
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

    def run(self) -> None:
        interval = self.starting_interval
        last_post = None
        while True:
            submissions = self._get_lasts_submissions()
            if last_post is not None:
                submissions = submissions[
                    submissions['created_utc'] > last_post['created_utc']
                ]
            self.exporter.export(submissions)

            if len(submissions) == 1000:
                interval -= self.interval_step
                interval = 1 if interval < 1 else interval
            elif submissions.empty:
                interval += self.interval_step

            last_post = submissions.iloc[0] if not submissions.empty else last_post
            print(f'{interval=}')
                