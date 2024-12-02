from dataclasses import dataclass, field
from enum import Enum
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.dataclasses import SnowLink

class EnumSyncType(Enum):
    HIST = "HIST"
    TRENDS = "TREND"

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


@dataclass
class Read:
    """
    Zabbix history or trend information
    """

    # item:Item = Item()
    timeUnix:int | None = None
    timeDatetime:str | None = None 
    timeStr:str | None = None 
    valu:int = None
    read_type:EnumReadType = None
    is_trend:bool = False
