import psycopg2, os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(override=True)

# Database connection parameters
db_params = {
    'host': os.getenv("zabbix_db_ip"),
    'dbname': os.getenv("zabbix_db_name"),
    'user': os.getenv("zabbix_db_user"),
    'password': os.getenv("zabbix_db_pwd"),
    'port': '3306'
}

# Calculate the timestamp for 3 months ago
three_months_ago = int((datetime.now() - timedelta(days=90)).timestamp())

# Connect to the Zabbix database
conn = psycopg2.connect(**db_params)
cursor = conn.cursor()
breakpoint()

# Query to get item IDs with the "ACCT" tag
query_item_ids = """
SELECT itemid FROM items
JOIN item_tag ON items.itemid = item_tag.itemid
WHERE item_tag.tag = 'ACCT';
"""
cursor.execute(query_item_ids)
item_ids = [row[0] for row in cursor.fetchall()]

# Query to get historical data for these items in the last 3 months
query_history = f"""
SELECT itemid, clock, value 
FROM history 
WHERE itemid = ANY(%s) AND clock >= %s;
"""
cursor.execute(query_history, (item_ids, three_months_ago))

# Fetch and process results
history_data = cursor.fetchall()

# Close the database connection
cursor.close()
conn.close()

# Display the results
for record in history_data:
    item_id, timestamp, value = record
    print(f"Item ID: {item_id}, Timestamp: {datetime.fromtimestamp(timestamp)}, Value: {value}")
