from .IZbxDB import IZbxDB 

import bisect
from collections import defaultdict
import time
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumSyncType, Item, Read, EnumReadType
from .IZbxDB import IZbxDB 

class NewZbxDB(IZbxDB):

    def __init__(self, *args):
        super().__init__(*args)

    def get_items_product_links(self, *args):
        # TODO query item.name: Total Traffic 
        # TODO query based on tags: ACCT, Rename Pending
        query_items = f"""
            SELECT item.itemid, item.name, item.interfaceid, item.uuid, item.hostid, host.host hostName 
            FROM items item
                JOIN hosts host ON item.hostid = host.hostid    
                LEFT JOIN item_tag ON item.itemid = item_tag.itemid
            WHERE (
                    item.name LIKE '%ACCT%'
                    or item.name LIKE '%Elea OnRamp%'
                    or item.name LIKE '%Elea Connect%'
                    or item.name Like '%Elea Metro Connect%' 
                ) and (
                    item_tag.tag LIKE 'Application'
                    and item_tag.value LIKE 'Total Interface Traffic'
                )
        """
                    # and item_tag.value IN ('Total Interface Traffic', 'Rename Pending')
                    # and item_tag.value LIKE 'Rename Pending'

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

        breakpoint()

        return reads 
