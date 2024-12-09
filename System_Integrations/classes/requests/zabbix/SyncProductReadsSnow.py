from datetime import datetime
import os
import time
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumReadType, EnumSyncType, Read
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinks import SnowProductLinks
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.ISnowProductLinks import ISnowProductLinks
from System_Integrations.classes.strategies.zabbix.ProductLinks.IZbxDB import IZbxDB
from System_Integrations.utils.netbox_api import get_circuits, get_tenants
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
            readType: EnumReadType = EnumReadType.TOTAL_TRAFFIC,
            dataType: EnumSyncType = EnumSyncType.HIST,
            avgTime: AvgTimeOptions = AvgTimeOptions.FIVE_MIN,
        ):
                
        self.db = db if db else self.db
        self.targetSystem = targetSystem if targetSystem else self.targetSystem
        self.readType = readType
        self.dataType = dataType
        self.avgTime = avgTime

        self.config = {
            EnumReadType.TOTAL_TRAFFIC: {
                "get_data": self.db.get_total_traffic,
                "get_most_recent_read_target_system": self.targetSystem.get_most_recent_read_time,
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
        netbox_circuits = get_circuits(netbox_url, netbox_headers) 

        accounts = self.targetSystem.get_accounts()
        links = self.targetSystem.get_product_links()
        mostRecentTime = self.search_config("get_most_recent_read_target_system")(self.dataType)
        if not mostRecentTime:
            if self.dataType == EnumSyncType.HIST:
                mostRecentTime = int(time.time())- 24 * 60 * 60 # 24 hours ago
            else:
                now = datetime.now()
                # Calculate one month ago manually
                if now.month == 1:  # If it's January, go to December of the previous year
                    one_month_ago = now.replace(year=now.year - 1, month=12)
                else:
                    # Otherwise, just subtract one month
                    one_month_ago = now.replace(month=now.month - 1)

                mostRecentTime = int(one_month_ago.timestamp())

        items = self.db.get_items_product_links()
        items = self.targetSystem.process_items_product_links(items, accounts, netbox_tenants, netbox_circuits, links)
        breakpoint()


        items = self.targetSystem.post_product_links(items)
        data = self.search_config("get_data")(
            type = self.dataType, 
            avgTime = self.avgTime,
            items = items, 
            mostRecentReadTime = mostRecentTime
        )

        self.search_config("post_data_target_system")(data, self.dataType)



