import bisect
from collections import defaultdict
import time
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumSyncType, Item, Read, EnumReadType
from commons.classes.utils import get_kwargs
from .IZbxDB import IZbxDB 

class OldZbxDB(IZbxDB):

    def __init__(self, *args, **kwargs):
        params = {**get_kwargs(), **kwargs}
        super().__init__(**params)

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


    def get_total_traffic(self, 
            type:EnumSyncType = EnumSyncType.HIST,
            items:list[Item]=[], 
            mostRecentReadTime = None,
            avgTime:AvgTimeOptions = AvgTimeOptions.FIVE_MIN,
            *args):
        
        # GETS BITS SENT e BITS RECEIVED (items that were queried in get_items_product_links)
        
        print("Creating quering db...")
        start = time.time()
        reads = self.get_reads_of_items(
            type = type, 
            items = items, 
            mostRecentReadTime = mostRecentReadTime,
            avgTime = avgTime,
        )
        end = time.time()
        duration = end - start
        print(f"\t=> took {duration:.2f} seconds")

        # CALCULATES THE TOTAL TRAFFIC BY PAIRING BITS SENT AND BITS RECEIVED
        read_types_to_sum = [EnumReadType.BITS_SENT, EnumReadType.BITS_RECEIVED]
        pair_dict = {}

        # Step 1: Group by (hostid, interface)
        print("Creating groups...")
        start = time.time()
        grouped_data = defaultdict(list)
        for read in reads:
            key = (read.item.host.id, read.item.interfaceName)
            grouped_data[key].append(read)


        end = time.time()
        duration = end - start
        print(f"\t=> took {duration:.2f} seconds")

        # Step 2: Pair by closest time
        pairs = []
        unmatched_sent = []
        max_time_diff = 120 # Allowable time difference in seconds
        print("Matching pairs... ")
        for key, measurements in grouped_data.items():
            # Separate by type
            sent = sorted([m for m in measurements if m.item.readType.value == EnumReadType.BITS_SENT.value], key=lambda x: x.time)
            received = sorted([m for m in measurements if m.item.readType.value == EnumReadType.BITS_RECEIVED.value], key=lambda x: x.time)

            # Extract times for binary search
            received_times = [m.time for m in received]
            used_indices = set()

            iterations = 0

            start = time.time()
            for s in sent[:]:
                # Find the closest time in "Bits Received" using binary search
                pos = bisect.bisect_left(received_times, s.time)
                closest_match = None
                closest_idx = None
                direction = 0  # 0 = not started, -1 = left, +1 = right
                
                while True:
                    if pos < len(received) and (direction >= 0):  # Check right neighbor
                        if pos not in used_indices:
                            closest_match = received[pos]
                            closest_idx = pos
                            break
                        pos += 1
                        direction = 1  # Move right
                    
                    if pos > 0 and (direction <= 0):  # Check left neighbor
                        if pos - 1 not in used_indices:
                            closest_match = received[pos - 1]
                            closest_idx = pos - 1
                            break
                        pos -= 1
                        direction = -1  # Move left
                    
                    # If neither direction finds a match
                    if direction > 0 and pos >= len(received) or direction < 0 and pos <= 0:
                        break
                
                # Validate match
                if closest_match and abs(s.time - closest_match.time) <= max_time_diff:
                    pairs.append((s, closest_match))
                    used_indices.add(closest_idx)  # Mark index as used
                else:
                    unmatched_sent.append(s)

                iterations += 1

        end = time.time()
        duration = end - start
        print(f"\t=> took {duration:.2f} seconds")

        # Step 3: Sum Pairs
        total_traffic_reads = []
        for match in pairs:
            value = match[0].value + match[1].value
            timeValue = match[0].time
            match_items = [match[0], match[1]]

            total_traffic_reads.append(Read(
                item = match_items[0].item,
                time = timeValue,
                value = value,
                sourceReads= match_items,
                isTrend = type == EnumSyncType.TRENDS
            ))


        return total_traffic_reads
