import array
from datetime import datetime
import json
import os
import argparse
import re

from dotenv import load_dotenv
from numpy import iinfo
import pandas as pd

from System_Integrations.utils.compare_utils import is_response_ok
from System_Integrations.utils.mapper import map_to_requests_response
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data, patch_servicenow_record, post_to_servicenow_table
from commons.pandas.utils import get_df_from_excel
from commons.utils.logging import save_file
from .Unveil import pathImports, sites, path as basePath
from ..CreateImports import pathImports as oldImportPath


# Script to fix little inconsistencies of snow_data

# Problem: "Type of cross" set as "Internal" was imported as empty in service now
# Fix: Take information from import file and insert into new data
for site in sites:
    df_import = get_df_from_excel(f"{oldImportPath}{site}/{site}_import.xlsx")
    dict_import = df_import.to_dict(orient="records")
    
    df_new = get_df_from_excel(f"{pathImports}{site}/snow_cross_{site}_data.xlsx")
    dict_new = df_new.to_dict(orient="records")
    for cross in dict_new:
        if not pd.isna(cross["Type of Cross"]): continue
        
        corr_cross = next((x for x in dict_import if x["ID Cross"] == cross["ID Cross"]), None)
        if not corr_cross: continue
        if not corr_cross["Tipo de Cross"]: continue

        cross["Type of Cross"] = corr_cross["Tipo de Cross"]
        
    df_new = pd.DataFrame.from_dict(dict_new)
    df_new.to_excel(f"{pathImports}{site}/snow_cross_{site}_data.xlsx", index=False) 