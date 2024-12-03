import os
from abc import ABC, abstractmethod

import pymysql
from System_Integrations.classes.requests.zabbix.dataclasses import EnumReadType, EnumSyncType, Item, Read
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

    def get_reads_of_items(self, 
            type:EnumSyncType = EnumSyncType.HIST,
            items:list[Item] = [], 
            mostRecentReadTime = None, 
            *args):
            
        aItemsIds = []
        items = items if items else self.items
        if items:
            aItemsIds = [x.id for x in items]
        
        where = []
        query = ""
        if type == EnumSyncType.HIST:
            query = f"""
                SELECT unit.itemid, unit.clock, unit.value, host.host hostName 
                FROM history_uint unit
                    JOIN items item ON unit.itemid = item.itemid
                    JOIN hosts host ON item.hostid = host.hostid
            """
        elif type == EnumSyncType.TRENDS:    
            query = f"""
                SELECT unit.itemid, unit.clock, unit.value_avg, host.host hostName 
                FROM trends_uint unit
                    JOIN items item ON unit.itemid = item.itemid
                    JOIN hosts host ON item.hostid = host.hostid
            """

        if not query: raise Exception(f"No SQL query implemented for type {type}")

        if items: 
            where.append(( 
                f"unit.itemid IN ({','.join(['%s'] * len(aItemsIds))})", # filter
                (*aItemsIds, ) # args
            ))
        if mostRecentReadTime:
            where.append((
                f"clock >= %s",
                (mostRecentReadTime, )
            ))

        if where:
            filters = []
            args = tuple()
            for filter in where:
                filters.append(filter[0])
                args += (*filter[1], )

            where = ""
            where += "WHERE " + (" AND ".join(filters))
            query += where
            
        self.cursor.execute(query, (*args, ))
        data = self.cursor.fetchall()

        aReads = []
        for read in data:
            itemCorr = next((x for x in items if read[0] == x.id), None)

            if not itemCorr: continue

            aReads.append(Read(
                item = itemCorr,
                time = read[1],
                value = read[2],
            ))

        return aReads
    
    def get_total_traffic(self, type:EnumSyncType = EnumSyncType.HIST, items:list[Item]=[], mostRecentReadTime = None,  *args):
        pass
