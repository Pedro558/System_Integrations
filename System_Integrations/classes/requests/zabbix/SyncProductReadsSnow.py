import os
from System_Integrations.classes.requests.zabbix.dataclasses import EnumReadType, EnumSyncType, Read
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinks import SnowProductLinks
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.ISnowProductLinks import ISnowProductLinks
from System_Integrations.classes.strategies.zabbix.ProductLinks.IZbxDB import IZbxDB
from System_Integrations.utils.netbox_api import get_tenants
from System_Integrations.utils.parser import get_value

from dotenv import load_dotenv
load_dotenv(override=True)

class SyncProductLinksSnow:
    """
    Request that contains the workflow of getting the reads from a Database and posting it to the target system

    Agrs:
    - db: Zbx
    - targetSystem: Snow

    """

    db: IZbxDB = IZbxDB()
    targetSystem: ISnowProductLinks = SnowProductLinks()

    def __init__(self, 
            db: IZbxDB | None, 
            targetSystem: SnowProductLinks | None,
            readType: EnumReadType = EnumReadType.TOTAL_INTERFACE_TRAFFIC,
            dataType: EnumSyncType = EnumSyncType.HIST,
        ):
                
        self.db = db if db else self.db
        self.targetSystem = targetSystem if targetSystem else self.targetSystem
        self.readType = readType
        self.dataType = dataType

        self.config = {
            EnumReadType.TOTAL_INTERFACE_TRAFFIC: {
                "get_data": self.db.get_total_traffic,
                "get_most_recent_read_target_system": self.targetSystem.get_most_recent_read,
                "post_data_target_system": self.targetSystem.post_total_traffic_reads,
            }
        }

    def search_config(self, 
            func:str | None,
            readType:EnumReadType | None = None, 
            dataType:EnumSyncType | None = None
        ):

        readType = readType if readType else self.readType
        dataType = dataType if dataType else self.dataType

        if not readType: raise ValueError("no value for readType")
        # if not dataType: raise ValueError("no value for dataType")

        configReadType = self.config[readType]
        if not configReadType: raise NotImplementedError(f"No implementation for reads {readType}")
        
        func = configReadType[func]
        return func

    def run(self):
        self.db.auth()
        self.db.connect()
        self.targetSystem.auth()

        # Netbox auth
        netbox_url = os.getenv("netbox_test_url")
        netbox_api_key = os.getenv("netbox_test_api_key")
        netbox_headers = {
            "Authorization": f"Token {netbox_api_key}"
        }
        netbox_tenants = get_tenants(netbox_url, netbox_headers) 

        accounts = self.targetSystem.get_accounts()
        links = self.targetSystem.get_product_links()
        mostRecent:Read = self.search_config("get_most_recent_read_target_system")()
        mostRecentTime = get_value(mostRecent, lambda x: x.time, None)

        items = self.db.get_items_product_links()
        items = self.targetSystem.process_items_product_links(items, accounts, netbox_tenants, links)

        items = self.targetSystem.post_product_links(items)
        breakpoint()
        mostRecentTime = 1730430000 #1733172884 # for tests
        data = self.search_config("get_data")(self.dataType, items, mostRecentTime)
        # data = self.search_config("process_data")(data)

        self.search_config("post_data_target_system")(data, self.dataType)



