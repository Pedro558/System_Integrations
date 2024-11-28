

from System_Integrations.classes.requests.zabbix.SyncProductReadsSnow import SyncProductLinksSnow
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinks import SnowProductLinks
from System_Integrations.classes.strategies.zabbix.ProductLinks.OldZbxDB import OldZbxDB

db = OldZbxDB()
targetSystem = SnowProductLinks()

request = SyncProductLinksSnow(db, targetSystem)
request.run()