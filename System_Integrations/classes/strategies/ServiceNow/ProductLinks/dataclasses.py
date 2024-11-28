from dataclasses import dataclass, field

@dataclass
class SnowLink:
    acct:str = field(default_factory=str)
    account_sys_id:str = field(default_factory=str)
    client_display_name:str = field(default_factory=str)