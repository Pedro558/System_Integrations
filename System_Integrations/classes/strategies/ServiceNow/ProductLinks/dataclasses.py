from dataclasses import dataclass, field

from System_Integrations.utils.parser import get_visual_commit_rate, parse_commit_rate_to

@dataclass
class SnowLink:
    sys_id:str = field(default_factory=str)
    acct:str = field(default_factory=str)
    cid:str = field(default_factory=str)
    linkType:str = field(default_factory=str)
    account_sys_id:str = field(default_factory=str)
    client_display_name:str = field(default_factory=str)
    commit_rate:int = field(default_factory=int)
    display_name:str = field(default_factory=str)

    def create_display_name(self, cid:str, cloud:str | None = None, origin:str | None = None, dest:str | None = None):
        name = ""
        name = f"{self.client_display_name} - {self.linkType}"
        if origin: name += f" - {origin}"
        if self.linkType == "Elea On Ramp":
            if origin and cloud: name += f":{cloud}"
        
        if self.linkType == "Elea Metro Connect":
            if origin and dest:
                name += f":{dest}"

        if self.commit_rate:
            banda = (
                f'{ parse_commit_rate_to(self.commit_rate*1000, "GB") } Gbps'.replace(".0","")
                if ( self.commit_rate * 1000 ) > 1e9 else  
                f'{ parse_commit_rate_to(self.commit_rate*1000, "MB") } Mbps'.replace(".0","")
            )
            name += f" - {banda}"

        if cid: name = f"{cid} ({name})"
        

        self.display_name = name
        return self
