from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.dataclasses import SnowLink

class EnumSyncType(Enum):
    HIST = "history"
    TRENDS = "trend"

class EnumReadType(Enum):
    BITS_SENT = "Bits sent"
    BITS_RECEIVED = "Bits received"
    TOTAL_INTERFACE_TRAFFIC = "Total Interface Traffic"

# More about dataclasses here: https://docs.python.org/3/library/dataclasses.html
@dataclass
class Host:
    id:int = field(default_factory=int)
    name:str = field(default_factory=str)

@dataclass
class Item:
    """
    Zabbix item information
    """

    id:int = field(default_factory=int)
    name:str = field(default_factory=str)
    interfaceId:int = field(default_factory=int)
    interfaceName:str = field(default_factory=str)
    uuid:str = field(default_factory=str)
    readType:EnumReadType = field(default_factory=str)
    host:Host = field(default_factory=Host)
    snowLink:SnowLink = field(default_factory=SnowLink)

    need_cid:bool = False # helps looking for links that need to be patternized


@dataclass
class Read:
    """
    Zabbix history or trend information
    """

    item:Item = field(default_factory=Item)
    time:Optional[int] = field(default_factory=int)
    timeDatetime:Optional[datetime] = None
    timeStr:Optional[str] = field(default_factory=str) #datetime.fromtimestamp(timeValue).strftime("%d-%m-%Y %H:%M:%S")
    value:int = field(default_factory=int)
    isTrend:bool = False
    calculated:bool = False
    sourceReads:list["Read"] = field(default_factory=list)

    def __post_init__(self):
        # Set dependent fields if `time` is provided
        if self.time is not None:
            self.timeDatetime = datetime.fromtimestamp(self.time)
            self.timeStr = self.timeDatetime.strftime("%m-%d-%Y %H:%M:%S")

    # @property
    # def time(self) -> int|None:
    #     return self._time

    # # not working, the values are correctly setted, but from outside the class the values do not change
    # # maybe something todo with @dataclass    
    # @time.setter
    # def time(self, value:int|None):
    #     if value:
    #         self._time = value
    #         self.timeDatetime = datetime.fromtimestamp(value)
    #         self.timeStr = self.timeDatetime.strftime("%d-%m-%Y %H:%M:%S")
