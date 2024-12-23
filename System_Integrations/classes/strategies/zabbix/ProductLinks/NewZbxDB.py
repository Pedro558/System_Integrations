from commons.classes.utils import get_kwargs
from .IZbxDB import IZbxDB 

import bisect
from collections import defaultdict
import time
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumSyncType, Item, Read, EnumReadType
from .IZbxDB import IZbxDB 

class NewZbxDB(IZbxDB):

    def __init__(self, *args, **kwargs):
        params = {**get_kwargs(), **kwargs}
        super().__init__(**params)

    def get_items_product_links(self, *args):
        # query_items = f"""
        #     SELECT item.itemid, item.name, item.interfaceid, item.uuid, item.hostid, host.host hostName 
        #     FROM items item
        #         JOIN hosts host ON item.hostid = host.hostid    
        #         LEFT JOIN item_tag ON item.itemid = item_tag.itemid
        #     WHERE (
        #             item.name LIKE '%ACCT%'
        #             or item.name LIKE '%Elea OnRamp%'
        #             or item.name LIKE '%Elea Connect%'
        #             or item.name LIKE '%Elea Internet Connect%'
        #             or item.name Like '%Elea Metro Connect%' 
        #         ) and (
        #             item.name LIKE '%Bits sent%'
        #             or 
        #             item.name LIKE '%Bits received%'
        #         ) 
        #         and item.name NOT LIKE '95 percentil%'
        # """
        
        # this is to avoid duplicates item in devices that collect the information from different tags (Bits sent and Bits received vs ACCT (TAGS))
        query_items = f"""
            WITH RankedItems AS (
                SELECT 
                    item.itemid,
                    item.name,
                    item.interfaceid,
                    item.uuid,
                    item.hostid,
                    host.host AS hostName,
                    item_tag.tag AS tagName,
                    ROW_NUMBER() OVER (
                        PARTITION BY item.hostid, item.interfaceid, item.name
                        ORDER BY 
                            CASE 
                                WHEN item_tag.tag LIKE '%ACCT%' THEN 1
                                ELSE 2
                            END
                    ) AS rank
                FROM 
                    items item
                    JOIN hosts host ON item.hostid = host.hostid    
                    LEFT JOIN item_tag ON item.itemid = item_tag.itemid
                WHERE (
                    item.name LIKE '%ACCT%'
                    OR item.name LIKE '%Elea OnRamp%'
                    OR item.name LIKE '%Elea Connect%'
                    OR item.name LIKE '%Elea Internet Connect%'
                    OR item.name LIKE '%Elea Metro Connect%'
                ) 
                AND (
                    item.name LIKE '%Bits sent%'
                    OR item.name LIKE '%Bits received%'
                ) 
                AND item.name NOT LIKE '95 percentil%'
            )
            SELECT 
                itemid, 
                name, 
                interfaceid, 
                uuid, 
                hostid, 
                hostName, 
                tagName
            FROM 
                RankedItems
            WHERE 
                rank = 1;
        """

        self.cursor.execute(query_items)
        self.items = self.cursor.fetchall()

        return self.items 


    def get_total_traffic(self, 
            type:EnumSyncType = EnumSyncType.HIST,
            items:list[Item]=[], 
            mostRecentReadTime = None, 
            avgTime:AvgTimeOptions = AvgTimeOptions.FIVE_MIN,
            *args):
        
        # GETS BITS SENT e BITS RECEIVED (items that were queried in get_items_product_links)
        
        print("Quering db...")
        start = time.time()
        reads = self.get_reads_of_items(
            type = type, 
            items = items, 
            avgTime = avgTime,
            mostRecentReadTime = mostRecentReadTime,
        )
        end = time.time()
        duration = end - start
        print(f"\t=> took {duration:.2f} seconds")

        return reads 
