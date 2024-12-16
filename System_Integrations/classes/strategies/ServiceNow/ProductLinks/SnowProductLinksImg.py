import base64
import json
import time
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO

import requests
from System_Integrations.classes.requests.zabbix.dataclasses import EnumRangeOptions, Item, Read
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.ISnowProductLinks import ISnowProductLinks
from System_Integrations.classes.strategies.Storage.IFileStorage import IFileStorage 
from System_Integrations.classes.strategies.Storage.dataclasses import File
from System_Integrations.utils.parser import group_by
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

    def process_total_traffic(self, reads:list[Read], items:list[Item]=None, type:EnumRangeOptions = EnumRangeOptions.LAST_DAY):

        start_time = time.time()
        print("Creating graphs...")
        for index, item in enumerate(items):
            item_reads = [(x.timeDatetime, x.valueMB) for x in reads if x.item.id == item.id]
            df = pd.DataFrame(item_reads, columns=["Time", "Total Traffic"])
            df['Time'] = pd.to_datetime(df['Time'])

            fig, ax = plt.subplots(figsize=(14, 7))

            # Plot the data with a smooth line and a fill for the area
            ax.plot(df['Time'], df['Total Traffic'], color='#0078D7', linewidth=2, label='Link Total Traffic Week')
            ax.fill_between(df['Time'], df['Total Traffic'], color='#0078D7', alpha=0.2)

            # Style adjustments
            ax.set_title('Link Total Traffic Week', fontsize=18, weight='bold', color='#34495E')
            ax.set_xlabel('', fontsize=14, color='#2E4053')  # Leave x-axis label blank for a clean look
            ax.set_ylabel('Total Traffic', fontsize=14, weight='bold', color='#2E4053')
            ax.tick_params(axis='x', labelsize=10, rotation=45, colors='#5D6D7E')
            ax.tick_params(axis='y', labelsize=12, colors='#5D6D7E')
            ax.grid(visible=True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)

            # Add a legend
            ax.legend(loc='upper right', fontsize=12, frameon=False)

            # Adjust layout for a clean look
            plt.tight_layout()

            # Save the figure for later
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            # item.graphBase64 = base64.b64encode(buf.read()).decode('utf-8')
            item.file = File(
                name=f"{item.snowLink.sys_id}_{type.value}",
                data=buf.read()
            )

            if not item.file.name: breakpoint()

            buf.close()
            plt.close(fig)

            print(f"\t{index+1}/{len(items)} done...")
            
        end_time = time.time()
        duration = end_time - start_time
        print(f"All done, took => {duration:.2f} seconds")
             
            # plt.savefig('traffic_graph.png', fig=item.graphImg, dpi=300)
            # item.graphImg.savefig('traffic_graph.png', dpi=300)
            # item.graphImg.show()


    def _post_read_img(self, items:list[Item], rangeType:Literal["daily", "weekly", "monthly"] = "daily"):
        for item in items:
            # folderLocation = "/Temp/ZabbixSnowSyncImg/TotalTraffic"
            # filePath = f"{folderLocation}/total_traffic.png" 
            # save_file(pathToSave=folderLocation, contentToSave="", fileName=".ignore") # make sure the path is created
            # item.graphImg.savefig(filePath)

            # with open(filePath, "rb") as img:
            # data = {
            #     "u_daily": base64.b64encode(img.read()).decode("utf-8"),
            #     "u_time": datetime.now().strftime("%Y-%m-%d %H:%M%S"),
            #     "u_link": item.snowLink.sys_id
            # }
            # files = {
            #     "u_daily": img,
            # }

            data = {
                "u_daily": item.graphBase64,
                "u_weekly": item.graphBase64,
                "u_monthly": item.graphBase64,
                "u_type": "Total Traffic",
                "u_link": item.snowLink.sys_id,
                "u_time": datetime.now().strftime("%Y-%m-%d %H:%M%S"),
            }

            url = self.snow_url + 'api/now/table/' + "u_link_reads_image"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer '+self.token,
            }

            # response = requests.post(url, headers=headers, params = {}, data=json.dumps(data))
            breakpoint()
            response = requests.post(url=self.snow_url+'/api/sn_entitlement/teste_scoped_licensing_engine/update_imgs', headers=headers, data = json.dumps(data))

          
    def post_total_traffic_reads(self, items:list[Item]=[], rangeType:EnumRangeOptions=EnumRangeOptions.LAST_DAY, *args, **kwargs):
        files = [x.file for x in items]
        self.fileStorage.upload(files) # due to object reference, the files inside the items, will be updated automatically

        reads_to_post = []
        for item in items:
            field = {
                EnumRangeOptions.LAST_DAY: "u_daily_url",
                EnumRangeOptions.LAST_WEEK: "u_weekly_url",
                EnumRangeOptions.LAST_MONTH: "u_monthly_url",
            }.get(rangeType )

            reads_to_post.append({
                field: item.file.url,
                "u_type": "Total Traffic",
                "u_link": item.snowLink.sys_id,
                "u_time": datetime.now().strftime("%Y-%m-%d %H:%M%S"),
            })

        response = client_monitoring_multi_post_img(self.snow_url, reads_to_post, self.token)

