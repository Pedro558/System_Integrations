

from System_Integrations.classes.requests.zabbix.SyncProductReadsSnow import SyncProductLinksSnow
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumSyncType
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinks import SnowProductLinks
from System_Integrations.classes.strategies.zabbix.ProductLinks.NewZbxDB import NewZbxDB
from System_Integrations.classes.strategies.zabbix.ProductLinks.OldZbxDB import OldZbxDB

db = OldZbxDB()
# db = NewZbxDB()
targetSystem = SnowProductLinks()

request = SyncProductLinksSnow(
    db, 
    targetSystem, 
    dataType = EnumSyncType.HIST,
    avgTime = AvgTimeOptions.FIVE_MIN,
)
request.run()