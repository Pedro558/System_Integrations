

from System_Integrations.classes.requests.zabbix.dataclasses import EnumReadType, EnumSyncType, Read
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinks import SnowProductLinks
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.ISnowProductLinks import ISnowProductLinks
from System_Integrations.classes.strategies.zabbix.ProductLinks.IZbxDB import IZbxDB
from System_Integrations.utils.parser import get_value


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
                EnumSyncType.HIST: {
                    "get_data": self.db.get_history_total_traffic,
                    "process_data": self.targetSystem.process_history_total_traffic,
                    "get_most_recent_read_target_system": self.targetSystem.get_most_recent_read,
                    "post_data_target_system": self.targetSystem.post_total_traffic_reads,
                },
                EnumSyncType.TRENDS: {
                    "get_data": self.db.get_trend_total_traffic,
                    "process_data": self.targetSystem.process_trend_total_traffic,
                    "get_most_recent_read_target_system": self.targetSystem.get_most_recent_read_trend,
                    "post_data_target_system": self.targetSystem.post_total_traffic_reads_trends,
                }
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
        if not dataType: raise ValueError("no value for dataType")

        configReadType = self.config[readType]
        if not configReadType: raise NotImplementedError(f"No implementation for reads f{readType}")

        configDataType = configReadType[dataType]
        if not configDataType: raise NotImplementedError(f"No implementation for data type f{dataType}")
        
        if not func: return configDataType
        func = configDataType[func]
        return func

    def run(self):
        self.db.auth()
        self.targetSystem.auth()

        self.targetSystem.get_accounts()
        mostRecent:Read = self.search_config("get_most_recent_read_target_system")()
        mostRecentTime = get_value(mostRecent, lambda x: x.time, None)

        items = self.db.get_items_product_links()
        self.targetSystem.process_items_product_links(items)

        data = self.search_config("get_data")(mostRecentTime)
        data = self.search_config("process_data")(data)

        self.search_config("post_data_target_system")(data)



