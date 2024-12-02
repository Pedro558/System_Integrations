import os
from abc import ABC, abstractmethod

import pymysql
from System_Integrations.classes.requests.zabbix.dataclasses import EnumReadType, EnumSyncType
from dotenv import load_dotenv

load_dotenv(override=True)

class IZbxDB(ABC):
    db_params = {
        'host': None,
        'database': None,
        'user': None,
        'password': None,
        'port': None,
    }

    def __init__(self, *args):
        self.conn = None
        self.cursor = None

    def auth(self, *args):
        # TODO get secrets from safe
        self.db_params = {
            'host': os.getenv("zabbix_db_ip"),
            'database': os.getenv("zabbix_db_name"),
            'user': os.getenv("zabbix_db_user"),
            'password': os.getenv("zabbix_db_pwd"),
            'port': 3306
        }

    def connect(self, *args):
        self.conn = pymysql.connect(**self.db_params)
        self.cursor = self.conn.cursor()

    def get_items_product_links(self, *args):
        pass
    
    def get_history_total_traffic(self, *args):
        pass

    def get_trend_total_traffic(self, *args):
        pass