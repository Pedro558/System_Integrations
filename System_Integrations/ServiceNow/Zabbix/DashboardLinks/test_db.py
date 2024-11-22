import pymysql, os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(override=True)

# Database connection parameters
db_params = {
    'host': os.getenv("zabbix_db_ip"),
    'database': os.getenv("zabbix_db_name"),
    'user': os.getenv("zabbix_db_user"),
    'password': os.getenv("zabbix_db_pwd"),
    'port': 3306
}

is_old_zabbix = db_params["host"] == "10.127.69.90"

three_months_ago = int((datetime.now() - timedelta(days=90)).timestamp())

# Connect to the Zabbix MariaDB database
conn = pymysql.connect(**db_params)
cursor = conn.cursor()

query_test = """
SHOW COLUMNS FROM items;
"""
# query_test = """
# SELECT * FROM item_tag WHERE item_tag.tag LIKE 'Application' and item_tag.value LIKE 'ACCT' LIMIT 5
# """
# query_test = """
# SELECT * FROM items LIMIT 5
# """
# query_test = f"""
# SELECT * FROM history_uint WHERE itemid in (77712) LIMIT 10 
# """
# query_test = f"""
# SELECT itemid, name 
# FROM items
# WHERE
#     name like '%\Bits%' 
#     and ( 
#         name LIKE '%ACCT%'
#         or name LIKE '%Elea OnRamp%'
#         or name LIKE '%Elea Connect%'
#         or name Like '%Elea Metro Connect%' 
#     )
# """
    # name LIKE 'Interface et-0/0/21(Elea OnRamp - Procergs - 5Gbps - PRI - POA1-SP4): Bits received' 
# WHERE itemid = '{item_ids[0]}'

cursor.execute(query_test)
results = [row for row in cursor.fetchall()]
print(results)
breakpoint()

# Query to get item IDs with the "ACCT" tag
query_item_ids = """
SELECT items.itemid, items.name FROM items
LEFT JOIN item_tag ON items.itemid = item_tag.itemid
WHERE
    (
        items.name LIKE '%\Bits%'
    )
"""
if not is_old_zabbix:
    query_item_ids += """
        and
        (
            item_tag.tag LIKE 'Application' 
            and item_tag.value LIKE 'ACCT'
        ) 
    """

cursor.execute(query_item_ids)
# item_ids = [row[0] for row in cursor.fetchall()]
result_items = [row for row in cursor.fetchall()]
if is_old_zabbix:
    result_items = [x for x in result_items if (
                                            "ACCT" in x[1]
                                            or "Elea Connect" in x[1]
                                            or "Elea OnRamp" in x[1]
                                            or "Elea Metro Connect" in x[1]
                                        )]
breakpoint()


item_ids = [row[0] for row in result_items]

# item_ids = map(str, item_ids)

# breakpoint()



item_ids = list(map(str, item_ids))

# Query to get historical data for these items in the last 3 months
query_history = f"""
SELECT itemid, clock, value 
FROM history_uint
WHERE itemid IN ({','.join(['%s'] * len(item_ids))})
"""
# WHERE itemid IN ({','.join(item_ids)})
# ORDER BY clock ASC 
# AND clock >= %s;
# WHERE itemid IN ({','.join(['%s'] * len(item_ids))}) AND clock >= %s;
cursor.execute(query_history, (*item_ids, ))

# Fetch and process results
history_data = cursor.fetchall()
breakpoint()

query_trends = f"""
SELECT itemid, clock, value_avg
FROM trends_uint
WHERE itemid IN ({','.join(['%s'] * len(item_ids))})
"""
# WHERE itemid IN ({','.join(item_ids[0:10])})
# AND clock >= %s;
cursor.execute(query_trends, (*item_ids, ))

# Fetch and process results
trends_data = cursor.fetchall()
breakpoint()

# Close the database connection
cursor.close()
conn.close()

# Display the results
for record in history_data:
    item_id, timestamp, value = record
    print(f"Item ID: {item_id}, Timestamp: {datetime.fromtimestamp(timestamp)}, Value: {value}")
