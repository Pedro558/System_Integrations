
import os
import re
from abc import ABC, abstractmethod
from random import randint
import time
from System_Integrations.classes.requests.zabbix.dataclasses import EnumSyncType, Host, Item, Read, EnumReadType
from datetime import datetime
from System_Integrations.classes.strategies.Storage.dataclasses import File
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.dataclasses import SnowLink
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import client_monitoring_multi_post, get_servicenow_auth_token, get_servicenow_table_data, patch_servicenow_record, post_to_servicenow_table
from dotenv import load_dotenv
from System_Integrations.utils.parser import group_by

load_dotenv(override=True)

class IFileStorage(ABC):

    def __init__(*args, **kwargs):
        pass
    
    def auth(self):
        pass

    def upload(self, files:list[File]):
        return files