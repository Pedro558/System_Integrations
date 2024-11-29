from System_Integrations.classes.requests.zabbix.dataclasses import Item, Read
from .IZbxDB import IZbxDB 

class OldZbxDB(IZbxDB):

    def __init__(self, *args):
        super().__init__(*args)

    def get_items_product_links(self, *args):
        query_items = f"""
            SELECT item.itemid, item.name, item.interfaceid, item.uuid, item.hostid, host.host hostName 
            FROM items item
                JOIN hosts host ON item.hostid = host.hostid
            WHERE
                item.name like '%\Bits%' 
                and ( 
                    item.name LIKE '%ACCT%'
                    or item.name LIKE '%Elea OnRamp%'
                    or item.name LIKE '%Elea Connect%'
                    or item.name Like '%Elea Metro Connect%' 
                )
        """

        self.cursor.execute(query_items)
        self.items = self.cursor.fetchall()
        return self.items 

    def get_history_total_traffic(self, 
            items:list[Item]=[], 
            mostRecentReadTime = None, 
            *args):

        aItemsIds = []
        items = items if items else self.items
        if items:
            aItemIds = [x.id for x in items]
        
        where = []
        args = []
        query_history = f"""
            SELECT hUnit.itemid, hUnit.clock, hUnit.value, host.host hostName 
            FROM history_uint hUnit
                JOIN items item ON hUnit.itemid = item.itemid
                JOIN hosts host ON item.hostid = host.hostid
        """

        if items: 
            where.append(( 
                f"hUnit.itemid IN ({','.join(['%s'] * len(aItemIds))})", # filter
                (*aItemIds, ) # args
            ))
        if mostRecentReadTime:
            where.append((
                f"clock <= %s",
                (mostRecentReadTime)
            ))

        if where:
            filters = []
            for filter in where:
                filters.append(filter[0])
                args.append(filter[1])

            where = ""
            where += "WHERE " + (" AND ".join(filters))
            query_history += where
            

        breakpoint()
        self.cursor.execute(query_history, (*args, ))
        history_data = self.cursor.fetchall()
        return history_data

    def get_trend_total_traffic(self, *args):
        pass