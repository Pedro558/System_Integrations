import os
from abc import ABC, abstractmethod

import pymysql
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumReadType, EnumSyncType, Item, Read
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
            avgTime:AvgTimeOptions = AvgTimeOptions.FIVE_MIN,
            *args):
            
        aItemsIds = []
        items = items if items else self.items
        if items:
            aItemsIds = [x.id for x in items]
        
        where = []
        query = ""
        
        tableConfig = {
            EnumSyncType.HIST: ("history_uint", "value"), # table name, value field
            EnumSyncType.TRENDS: ("trends_uint", "value_avg"),
        }

        if True:
            query = f"""
                SELECT
                    itemid,
                    FLOOR(clock / {avgTime.value[1]}) * {avgTime.value[1]} AS time_group,
                    AVG({tableConfig.get(type)[1]}) AS value
                FROM
                    {tableConfig.get(type)[0]}
                <WHERE>
                GROUP BY
                    itemid,
                    time_group
                ORDER BY
                    time_group;
            """

        if not query: raise Exception(f"No SQL query implemented for type {type}")

        if items: 
            where.append(( 
                f"itemid IN ({','.join(['%s'] * len(aItemsIds))})", # filter
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
            query = query.replace("<WHERE>", where)
        else:
            query = query.replace("<WHERE>", "")
            
        breakpoint()
        self.cursor.execute(query, (*args, ))
        data = self.cursor.fetchall()

        aReads = []
        for read in data:
            itemCorr = next((x for x in items if read[0] == x.id), None)

            if not itemCorr: continue

            aReads.append(Read(
                item = itemCorr,
                time = read[1],
                value = int(read[2]),
            ))

        return aReads
    
    def get_total_traffic(self, type:EnumSyncType = EnumSyncType.HIST, items:list[Item]=[], mostRecentReadTime = None,  *args):
        pass
