import base64
import json
import time
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO

import requests
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumRangeOptions, EnumReadType, Item, Read
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.ISnowProductLinks import ISnowProductLinks
from System_Integrations.classes.strategies.Storage.IFileStorage import IFileStorage 
from System_Integrations.classes.strategies.Storage.dataclasses import File
from System_Integrations.utils.parser import group_by, parse_commit_rate_to
from typing import Literal, Optional

from System_Integrations.utils.servicenow_api import client_monitoring_multi_post_img, post_to_servicenow_table
from commons.classes.utils import get_kwargs 
from commons.utils.logging import save_file



class SnowProductLinksImg(ISnowProductLinks):

    def __init__(self, 
                 fileStorage:IFileStorage | None,
                 *args, **kwargs
                 ):
        params = {**get_kwargs(), **kwargs}
        super().__init__(**params) 
        self.fileStorage = fileStorage or IFileStorage()

    def auth(self, *args, **kwargs):
        super().auth()
        self.fileStorage.auth()

    def get_most_recent_read_time(self, *args):
        return None # must return None, because to build the graph we need all the last corresponding period (24h, 7d, 30d)

    def process_total_traffic(self, 
                              reads:list[Read], 
                              items:list[Item]=None, 
                              rangeType:EnumRangeOptions = EnumRangeOptions.LAST_DAY, 
                              avgTime:AvgTimeOptions = None,
                              startDate:int = None,
                            ):

        start_time = time.time()
        print("Creating graphs...")
        
        grouped_items = group_by(items, ["snowLink.cid"])
        links = grouped_items.keys()

        for index, key in enumerate(links):
            try:
                
                item:list[Item] = grouped_items[key]
                item_sent = next((x for x in item if x.readType == EnumReadType.BITS_SENT), None)
                item_received = next((x for x in item if x.readType == EnumReadType.BITS_RECEIVED), None)

                if not item_sent or not item_received: breakpoint()
                if item_sent.file.data or item_received.file.data: breakpoint() 

                item_reads_sent = [(x.timeDatetime, x.valueMB) for x in reads if x.item.id == item_sent.id]
                item_reads_received = [(x.timeDatetime, x.valueMB) for x in reads if x.item.id == item_received.id]


                # Create DataFrames for both
                df_sent = pd.DataFrame(item_reads_sent, columns=["Time", "Upload Traffic"])
                df_received = pd.DataFrame(item_reads_received, columns=["Time", "Download Traffic"])

                # Ensure the Time column is in datetime format
                df_sent['Time'] = pd.to_datetime(df_sent['Time'])
                df_received['Time'] = pd.to_datetime(df_received['Time'])

                # Convert traffic values to Mbps
                df_sent['Upload Traffic'] *= 8  # Convert MB to Mbps
                df_received['Download Traffic'] *= 8  # Convert MB to Mbps

                # Define traffic limit in Mbps
                traffic_limit = 0
                if item_sent.snowLink.commit_rate:
                    traffic_limit = parse_commit_rate_to(item_sent.snowLink.commit_rate*1000, "MB")
                    

                # Create a figure and axis
                fig, ax = plt.subplots(figsize=(14, 7))

                # Plot download (bits received)
                ax.plot(df_received['Time'], df_received['Download Traffic'], color='#2E86C1', linewidth=2, label='Download Traffic')
                ax.fill_between(df_received['Time'], df_received['Download Traffic'], color='#2E86C1', alpha=0.2)

                # Plot upload (bits sent)
                ax.plot(df_sent['Time'], df_sent['Upload Traffic'], color='#E74C3C', linewidth=2, label='Upload Traffic')
                ax.fill_between(df_sent['Time'], df_sent['Upload Traffic'], color='#E74C3C', alpha=0.2)

                # Add a horizontal line for the traffic limit
                if traffic_limit:
                    ax.axhline(traffic_limit, color='orange', linewidth=1.5, linestyle='--')

                # Add a text label for the limit that adapts to the y-axis scale
                def format_traffic(value):
                    """Format traffic value to Mbps or Gbps."""
                    if value >= 1000:  # Convert to Gbps if value exceeds 1000 Mbps
                        return f"{value / 1000:.1f} Gbps"
                    return f"{value:.0f} Mbps"

                # Display the limit value in Mbps or Gbps
                formatted_limit = format_traffic(traffic_limit)

                # Set scale and format the y-axis
                def format_yaxis(value, _):
                    if value >= 1000:  # Convert to Gbps if traffic exceeds 1000 Mbps
                        return f"{value / 1000:.1f} Gbps"
                    return f"{value:.0f} Mbps"

                ax.yaxis.set_major_formatter(plt.FuncFormatter(format_yaxis))

                # Style adjustments
                ax.set_xlabel('Date', fontsize=14, weight='bold', color='#2E4053')  # X-axis label
                ax.set_ylabel('Traffic', fontsize=14, weight='bold', color='#2E4053')
                ax.tick_params(axis='x', labelsize=10, rotation=90, colors='#5D6D7E')  # No tilt for x-axis labels
                ax.tick_params(axis='y', labelsize=12, colors='#5D6D7E')
                ax.grid(visible=True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)

                start_date = datetime.fromtimestamp(startDate)
                end_date = datetime.now()
                ax.set_xlim([start_date, end_date])

                # Add a legend
                # ax.legend(loc='upper right', fontsize=12, frameon=False)
                ax.legend(
                    loc='upper right', 
                    fontsize=12, 
                    frameon=False,
                    labels=['Download Traffic', 'Upload Traffic', f'Limit: {formatted_limit}'], 
                    handles=[
                        plt.Line2D([], [], color='#2E86C1', linewidth=2),
                        plt.Line2D([], [], color='#E74C3C', linewidth=2),
                        plt.Line2D([], [], color='orange', linewidth=1.5, linestyle='--')
                    ]
                )

                # Add title below the graph

                title = "Download vs Upload"
                if avgTime:
                    title += {
                        AvgTimeOptions.FIVE_MIN: " ( Average 5 minutes ) ",
                        AvgTimeOptions.ONE_HOUR: " ( Average 1 hour ) ",
                        AvgTimeOptions.ONE_DAY: " ( Average 1 day ) ",
                    }.get(avgTime)

                fig.text(0.5, 0.01, title, fontsize=18, weight='bold', color='#34495E', ha='center')

                # Adjust layout for a clean look
                plt.tight_layout(rect=[0, 0.03, 1, 1])  # Reserve space for the title at the bottom

                buf = BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight")

                # with open("/Temp/test.png", "wb") as f:
                #     f.write(buf.getvalue())

                # breakpoint()

                item_sent.file = File(
                        name=f"{item_sent.snowLink.sys_id}_{rangeType.value}.png",
                        data=buf.getvalue()
                    )
                item_received.file = item_sent.file

                # Save the figure for later

                buf.close()
                plt.close(fig)

                print(f"\t{index+1}/{len(links)} done...")
            except Exception as e:
                breakpoint()
                print(e)



         
        # for index, item in enumerate(items):
        #     item_reads = [(x.timeDatetime, x.valueMB) for x in reads if x.item.id == item.id]
        #     df = pd.DataFrame(item_reads, columns=["Time", "Total Traffic"])
        #     df['Time'] = pd.to_datetime(df['Time'])

        #     fig, ax = plt.subplots(figsize=(14, 7))

        #     # Plot the data with a smooth line and a fill for the area
        #     ax.plot(df['Time'], df['Total Traffic'], color='#0078D7', linewidth=2, label='Link Total Traffic Week')
        #     ax.fill_between(df['Time'], df['Total Traffic'], color='#0078D7', alpha=0.2)

        #     # Style adjustments
        #     ax.set_title('Link Total Traffic Week', fontsize=18, weight='bold', color='#34495E')
        #     ax.set_xlabel('', fontsize=14, color='#2E4053')  # Leave x-axis label blank for a clean look
        #     ax.set_ylabel('Total Traffic', fontsize=14, weight='bold', color='#2E4053')
        #     ax.tick_params(axis='x', labelsize=10, rotation=45, colors='#5D6D7E')
        #     ax.tick_params(axis='y', labelsize=12, colors='#5D6D7E')
        #     ax.grid(visible=True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)

        #     # Add a legend
        #     ax.legend(loc='upper right', fontsize=12, frameon=False)

        #     # Adjust layout for a clean look
        #     plt.tight_layout()

        #     # Save the figure for later
        #     buf = BytesIO()
        #     fig.savefig(buf, format="png", bbox_inches="tight")
        #     buf.seek(0)
        #     # item.graphBase64 = base64.b64encode(buf.read()).decode('utf-8')
        #     item.file = File(
        #         name=f"{item.snowLink.sys_id}_{type.value}",
        #         data=buf.read()
        #     )

        #     if not item.file.name: breakpoint()

        #     buf.close()
        #     plt.close(fig)

        #     print(f"\t{index+1}/{len(items)} done...")
            
        end_time = time.time()
        duration = end_time - start_time
        print(f"All done, took => {duration:.2f} seconds")
             
            

    def post_total_traffic_reads(self, items:list[Item]=[], rangeType:EnumRangeOptions=EnumRangeOptions.LAST_DAY, *args, **kwargs):
        grouped_items = group_by(items, ["snowLink.sys_id"])

        files = [grouped_items[key][0].file for key in grouped_items.keys()]
        
        files_nf = [x for x in items if not x.file.name]
        if files_nf: breakpoint()
        
        self.fileStorage.upload(files) # due to object reference, the files inside the items, will be updated automatically

        reads_to_post = []
        for item in items:
            field = {
                EnumRangeOptions.LAST_DAY: "u_daily_url",
                EnumRangeOptions.LAST_WEEK: "u_weekly_url",
                EnumRangeOptions.LAST_MONTH: "u_monthly_url",
            }.get(rangeType)

            reads_to_post.append({
                field: item.file.url,
                "u_type": "Total Traffic",
                "u_link": item.snowLink.sys_id,
                "u_time": datetime.now().strftime("%Y-%m-%d %H:%M%S"),
            })

        response = client_monitoring_multi_post_img(self.snow_url, reads_to_post, self.token)

