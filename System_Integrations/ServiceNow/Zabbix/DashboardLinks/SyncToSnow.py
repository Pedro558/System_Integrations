

from System_Integrations.classes.requests.zabbix.SyncProductReadsSnow import SyncProductLinksSnow
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumRangeOptions, EnumSyncType
from System_Integrations.classes.strategies.Azure.BlobStorage import BlobStorage
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinks import SnowProductLinks
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinksImg import SnowProductLinksImg
from System_Integrations.classes.strategies.zabbix.ProductLinks.NewZbxDB import NewZbxDB
from System_Integrations.classes.strategies.zabbix.ProductLinks.OldZbxDB import OldZbxDB

# db = OldZbxDB()
db = NewZbxDB()
# targetSystem = SnowProductLinks()
targetSystem = SnowProductLinksImg(
    fileStorage = BlobStorage()
)

request = SyncProductLinksSnow(
    db,
    targetSystem,
    dataType = EnumSyncType.TRENDS,
    avgTime = AvgTimeOptions.ONE_DAY,
    rangeType = EnumRangeOptions.LAST_MONTH,
)
request.run()