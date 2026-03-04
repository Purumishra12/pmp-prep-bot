from pydantic import BaseModel
from typing import List


class Topic(BaseModel):
    slug: str
    name: str
    domain: str
    description: str
    keywords: List[str]
    source_tags: List[str]
    difficulty_levels: List[str]


class TopicGroup(BaseModel):
    domain: str
    domain_label: str
    topics: List[Topic]