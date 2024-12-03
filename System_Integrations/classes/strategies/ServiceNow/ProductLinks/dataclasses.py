from dataclasses import dataclass, field

@dataclass
class SnowLink:
    sys_id:int = field(default_factory=int)
    acct:str = field(default_factory=str)
    cid:str = field(default_factory=str)
    linkType:str = field(default_factory=str)
    account_sys_id:str = field(default_factory=str)
    client_display_name:str = field(default_factory=str)