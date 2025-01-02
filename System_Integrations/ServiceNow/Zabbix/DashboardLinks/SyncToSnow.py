import os

from System_Integrations.classes.factory.zabbix.SyncToSnowFactory import SyncToSnowFactory
from System_Integrations.classes.requests.zabbix.SyncProductReadsSnow import SyncProductLinksSnow
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumRangeOptions, EnumSyncType
from System_Integrations.classes.strategies.Azure.BlobStorage import BlobStorage
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinks import SnowProductLinks
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinksImg import SnowProductLinksImg
from System_Integrations.classes.strategies.zabbix.ProductLinks.NewZbxDB import NewZbxDB
from System_Integrations.classes.strategies.zabbix.ProductLinks.OldZbxDB import OldZbxDB

# db = OldZbxDB()
# db = NewZbxDB()
# targetSystem = SnowProductLinksImg(
#     fileStorage = BlobStorage()
# )


dataType = os.getenv("RD_OPTION_DATA_TYPE")
# dataType = EnumSyncType.HIST.value
dataType = EnumSyncType(dataType)

avgTime = os.getenv("RD_OPTION_AVG_TIME")
# avgTime = AvgTimeOptions.FIVE_MIN.value[0]
avgTime = AvgTimeOptions.get(avgTime)

rangeType = os.getenv("RD_OPTION_RANGE_TYPE")
# rangeType = EnumRangeOptions.LAST_DAY.value
rangeType = EnumRangeOptions(rangeType)

env = os.getenv("RD_OPTION_ENV")

factory = SyncToSnowFactory()
db = factory.create_db(source="new") 
targetSystem = factory.create_snow_processor(info_as="image", env=env)

request = SyncProductLinksSnow(
    db,
    targetSystem,
    dataType = dataType,
    avgTime = avgTime,
    rangeType = rangeType,
)
request.run()