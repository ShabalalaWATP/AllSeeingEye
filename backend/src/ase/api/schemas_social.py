"""Social listening board responses."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel

from ase.api.schemas_events import EventOut
from ase.application.trackers.social import SocialBoard


class SocialPlatformOut(BaseModel):
    platform: str
    instance: str
    count: int
    located: int


class SocialHashtagOut(BaseModel):
    tag: str
    count: int


class SocialKeywordOut(BaseModel):
    term: str
    count: int
    baseline: float | None
    baseline_hours: int
    ratio: float | None
    burst: bool


class SocialBoardOut(BaseModel):
    total: int
    located: int
    platforms: list[SocialPlatformOut]
    hashtags: list[SocialHashtagOut]
    keywords: list[SocialKeywordOut]
    posts: list[EventOut]
    window_start: datetime
    window_end: datetime
    keyword_hour: datetime

    @classmethod
    def from_board(cls, board: SocialBoard) -> Self:
        return cls(
            total=board.total,
            located=board.located,
            platforms=[
                SocialPlatformOut(
                    platform=row.platform,
                    instance=row.instance,
                    count=row.count,
                    located=row.located,
                )
                for row in board.platforms
            ],
            hashtags=[SocialHashtagOut(tag=row.tag, count=row.count) for row in board.hashtags],
            keywords=[
                SocialKeywordOut(
                    term=row.term,
                    count=row.count,
                    baseline=row.baseline,
                    baseline_hours=row.baseline_hours,
                    ratio=row.ratio,
                    burst=row.burst,
                )
                for row in board.keywords
            ],
            posts=[EventOut.from_event(event) for event in board.posts],
            window_start=board.window_start,
            window_end=board.window_end,
            keyword_hour=board.keyword_hour,
        )
