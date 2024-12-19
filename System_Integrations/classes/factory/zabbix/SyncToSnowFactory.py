

from ipaddress import ip_address
import os
from typing import Literal

from System_Integrations.classes.strategies.Azure.BlobStorage import BlobStorage
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinksImg import SnowProductLinksImg
from System_Integrations.classes.strategies.zabbix.ProductLinks.IZbxDB import IZbxDB
from System_Integrations.classes.strategies.zabbix.ProductLinks.NewZbxDB import NewZbxDB
from System_Integrations.classes.strategies.zabbix.ProductLinks.OldZbxDB import OldZbxDB

from dotenv import load_dotenv
load_dotenv(override=True)

class SyncToSnowFactory:

    zbxDbs = [
        NewZbxDB(
            ipaddress="10.11.70.92", database="zabbix",
            user="zabbix", secretName=""
        ),
        OldZbxDB(
            ipaddress="10.127.69.90", database="zabbix",
            user="zabbix", secretName=""
        ),
    ]

    def __init__(self,
                source:Literal["old", "new", "dynamic"] = "dynamic",
                style:Literal["image"] = "image" 
                ):
        self.source = source
        self.style = style


    def create_db(self, source:Literal["old", "new", "dynamic"] = "dynamic"):
        db = None

        db_options:list[IZbxDB] = []
        if source == "dynamic": db_options = self.zbxDbs
        elif source == "old": db_options = [x for x in self.zbxDbs if isinstance(x, OldZbxDB)]
        elif source == "new": db_options = [x for x in self.zbxDbs if isinstance(x, NewZbxDB)]
            
        for _db in db_options:
            _db.auth()
            _db.connect()
            db = _db
            break

        if not db: raise Exception("It was not possible to establish connection to the database.")

        return db

    def create_snow_processor(self, info_as:Literal["image"] = "image", env:Literal["dev","prd"]="dev"):
        targetSystem = None
        
        if info_as == "image":
            targetSystem = SnowProductLinksImg(
                env=env,
                # For local testing
                clientId = os.getenv("snow_client_id"),
                clientSecret = os.getenv("snow_client_secret"),
                refreshToken = os.getenv("snow_refresh_token"),

                fileStorage = BlobStorage()
            )

        if not targetSystem: raise Exception("It was not possible to create snow processor.")

        return targetSystem  






