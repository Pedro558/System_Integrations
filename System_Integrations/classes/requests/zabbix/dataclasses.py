from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.dataclasses import SnowLink

class AvgTimeOptions(Enum):
    ONE_MIN = ("ONE_MIN", 60)
    FIVE_MIN = ("FIVE_MIN", 60*5)
    ONE_HOUR = ("ONE_HOUR", 60*60)
    ONE_DAY = ("ONE_DAY", 60*60*24)

class EnumSyncType(Enum):
    HIST = "history"
    TRENDS = "trend"

class EnumReadType(Enum):
    BITS_SENT = "Bits sent"
    BITS_RECEIVED = "Bits received"
    TOTAL_TRAFFIC = "Total Traffic"

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
    valueTB:float = field(default_factory=float)
    valueGB:float = field(default_factory=float)
    valueMB:float = field(default_factory=float)
    valueKB:float = field(default_factory=float)
    isTrend:bool = False
    calculated:bool = False
    sourceReads:list["Read"] = field(default_factory=list)

    def __post_init__(self):
        # Set dependent fields if `time` is provided
        if self.time is not None:
            self.timeDatetime = datetime.fromtimestamp(self.time)
            self.timeStr = self.timeDatetime.strftime("%m-%d-%Y %H:%M:%S")
        
        if self.value:
            self.valueTB = float(self.value / (1e12 * 8)) 
            self.valueGB = float(self.value / (1e9 * 8))
            self.valueMB = float(self.value / (1e6 * 8))
            self.valueKB = float(self.value / (1e3 * 8))

    # @property
    # def value(self) -> int|None:
    #     return self._value

    # # not working, the values are correctly setted, but from outside the class the values do not change
    # # maybe something todo with @dataclass    
    # @value.setter
    # def value(self, value:int|None):
    #     if value:
    #         self._value = value
    #         self.valueTB = int(self._value / (1e12 * 8)) 
    #         self.valueGB = int(self._value / (1e9 * 8))
    #         self.valueMB = int(self._value / (1e6 * 8))
    #         self.valueKB = int(self._value / (1e3 * 8))