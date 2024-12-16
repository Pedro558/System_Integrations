from datetime import datetime
from dataclasses import dataclass, field
from typing import BinaryIO

@dataclass
class File():
    path: str = field(default_factory=str)
    name: str = field(default_factory=str)
    data: BinaryIO | str | None = field(default_factory=lambda: None)
    url: str | None = field(default_factory=lambda: None)