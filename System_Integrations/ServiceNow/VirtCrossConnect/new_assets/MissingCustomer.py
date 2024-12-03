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


# All Items of old cross table in PRD Snow were missing customers columns information (Customer A, Customer B and Fincal Customer) 

# Problem: Info extracted from old cross table is missing customer column information
# Fix: Retrieve missing information from excel that were used to populated the same info in PRD (this avoids having to do the upload information to snow again)
# Just change the paths names and dont worry
# python -m System_Integrations.ServiceNow.VirtCrossConnect.new_assets.MissingCustomer


new = get_df_from_excel("C:/Users/filipe.uccelli/source/System_Integration/System_Integrations/ServiceNow/VirtCrossConnect/new_assets/MissingCustomerProblem/snow_cross_SPO1_data.xlsx", [])
old = get_df_from_excel("C:/Users/filipe.uccelli/source/System_Integration/System_Integrations/ServiceNow/VirtCrossConnect/new_assets/MissingCustomerProblem/SPO1_import.xlsx", [])

breakpoint()

map_customer_a = old.set_index('ID Cross')['Cliente Ponta A'].to_dict()
map_customer_b = old.set_index('ID Cross')['Cliente Ponta B'].to_dict()
map_final_customer = old.set_index('ID Cross')['Cliente Final'].to_dict()

# Apply maps to overwrite columns in new
new['Tip A customer'] = new['ID Cross'].map(map_customer_a).combine_first(new['Tip A customer'])
new['Tip B customer'] = new['ID Cross'].map(map_customer_b).combine_first(new['Tip B customer'])
new['Final Customer'] = new['ID Cross'].map(map_final_customer).combine_first(new['Final Customer'])

print(new)
new.to_excel("C:/Users/filipe.uccelli/source/System_Integration/System_Integrations/ServiceNow/VirtCrossConnect/new_assets/MissingCustomerProblem/SPO1_fixed.xlsx")

