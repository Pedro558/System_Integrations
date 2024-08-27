import os

from commons.pandas.utils import *

from System_Integrations.auth.api_secrets import get_api_token
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from dotenv import load_dotenv

load_dotenv(override=True)

url_snow = os.getenv("snow_url")

pattern = re.compile(r'^[A-Za-z0-9\-]+:[A-Za-z0-9\-]+:[A-Za-z0-9\-]+:[A-Za-z0-9\-\\\/]+$')


def replace_data_hall(value, lookup_data_hall_dict):
    try:
        if pd.isna(value):  # Skip NaN values
            return value
        if pattern.match(value):
            # if value == "DH01:BL24:PP01:PT02": breakpoint()
            parts = value.split(':')
            para = lookup_data_hall_dict.get(parts[0], parts[0])
            parts[0] = para if isinstance(para, str) else value  # Replace Data Hall part
            return ':'.join(parts)
        else:
            return "[INVALID_FORMAT]=>"+value
    except:
        return "[INVALID_FORMAT]=>"+value
    
def replace_rack(value, lookup_data_hall_dict):
    try:
        if pd.isna(value):  # Skip NaN values
            return value
        if pattern.match(value):
            # if value == "DH01:BL24:PP01:PT02": breakpoint()
            parts = value.split(':')
            parts[1] = lookup_data_hall_dict.get(parts[1], parts[1])  # Replace Data Hall part
            return ':'.join(parts)
        else:
            return value
            return "[INVALID_FORMAT]=>"+value
    except:
        return value
    
    

sites = ["RJO1", "SPO1", "POA1", "CTA1", "BSB2"]
path = "C:/Users/filipe.uccelli/source/System_Integration/System_Integrations/ServiceNow/VirtCrossConnect/"
pathImports = f"{path}import/"

lookup_customer_all = get_df_from_excel(pathImports+"_lookups/de_para_customer.xlsx", {"De": [], "Para": []})
lookup_data_hall_all = get_df_from_excel(pathImports+"_lookups/de_para_data_hall.xlsx", {"De": [], "Para": []})
lookup_rack_all = get_df_from_excel(pathImports+"_lookups/de_para_rack.xlsx", {"De": [], "Para": []})

for site in sites:
    df = get_df_from_excel(f"{pathImports}/{site}/cross_{site}_data.xlsx")
    if df.empty: continue

    lookup_customer = lookup_customer_all[lookup_customer_all["Site"] == site]
    lookup_data_hall = lookup_data_hall_all[lookup_data_hall_all["Site"] == site]
    lookup_rack = lookup_rack_all[lookup_rack_all["Site"] == site]

    df_import = get_df_from_excel(f"{pathImports}{site}_import.xlsx")

    df["Site"] = site
    saltos = [col for col in df.columns if col.startswith('Salto')]

    # Merge df

    # use lookup to replace:
    # => customer (Cliente Ponta A / Cliente Ponta B)
    lookup_customer_dict = pd.Series(lookup_customer.Para.values, index=lookup_customer.De).to_dict()
    df['Cliente Ponta A'] = df['Cliente Ponta A'].map(lookup_customer_dict).fillna(df['Cliente Ponta A'])
    df['Cliente Ponta B'] = df['Cliente Ponta B'].map(lookup_customer_dict).fillna(df['Cliente Ponta B'])
    df['Cliente Final'] = df['Cliente Final'].map(lookup_customer_dict).fillna(df['Cliente Final'])

    # => data hall (Data Hall / Data Hall Ponta B / Saltos)
    # saltos = ["Salto 1", "Salto 2", "Salto 3", "Salto 4", "Salto 5"]

    lookup_data_hall_dict = pd.Series(lookup_data_hall.Para.values, index=lookup_data_hall.De).to_dict()
    df['Data Hall'] = df['Data Hall'].map(lookup_data_hall_dict).fillna(df['Data Hall'])
    df['Data Hall Ponta B'] = df['Data Hall Ponta B'].map(lookup_data_hall_dict).fillna(df['Data Hall Ponta B'])
    invalid_entries_dh = pd.DataFrame(columns=df.columns)
    
    
    for salto in saltos:
        # df[salto] = df[salto].apply(lambda value: replace_data_hall(value, lookup_data_hall_dict))
        processed_values = df[salto].apply(lambda value: replace_data_hall(value, lookup_data_hall_dict))
        processed_values = processed_values.fillna("")
        invalid_rows = processed_values[processed_values.notna() & processed_values.str.startswith("[INVALID_FORMAT]=>")]
        processed_values = processed_values.str.replace("[INVALID_FORMAT]=>", "")
        invalid_rows = invalid_rows.str.replace("[INVALID_FORMAT]=>", "")
        invalid_rows = df[df[salto].isin(invalid_rows)]
        # invalid_rows[salto] = invalid_rows[salto].str.replace("[INVALID_FORMAT]=>", "")
        if not invalid_rows.empty:
            invalid_rows = invalid_rows[["ID Cross", salto]]
            invalid_entries_dh = pd.concat([invalid_entries_dh, invalid_rows])

        df[salto] = processed_values

    # if site == "CTA1": breakpoint()
    invalid_entries_dh["Site"] = site
    invalid_entries_dh["Problem"] = "INVALID FORMAT"
    invalid_entries_dh = invalid_entries_dh[["Site", "ID Cross", "Problem"]+saltos]


    # => racks (Rack Ponta A / Rack Ponta B / Saltos)
    lookup_rack_dict = pd.Series(lookup_rack.Para.values, index=lookup_rack.De).to_dict()
    df['Rack Ponta A'] = df['Rack Ponta A'].map(lookup_rack_dict).fillna(df['Rack Ponta A'])
    df['Rack Ponta B'] = df['Rack Ponta B'].map(lookup_rack_dict).fillna(df['Rack Ponta B'])
    invalid_entries_rack = pd.DataFrame(columns=df.columns)
    for salto in saltos:
        processed_values = df[salto].apply(lambda value: replace_rack(value, lookup_rack_dict))
        # invalid_rows = processed_values[processed_values.notna() & processed_values.str.startswith("[INVALID_FORMAT]=>")]
        # invalid_rows = invalid_rows.str.replace("[INVALID_FORMAT]=>", "")
        # invalid_rows = df[df[salto].isin(invalid_rows)]
        # Execução disso no data hall já levanta os saltos invalidos
        # if not invalid_rows.empty:
        #     invalid_rows["Site"] = site
        #     invalid_rows["Problem"] = "INVALID FORMAT"
        #     invalid_rows = invalid_rows[["Site", "ID Cross", "Problem", salto]]
        #     invalid_entries_rack = pd.concat([invalid_entries_rack, invalid_rows])

        df[salto] = processed_values

    # invalid_entries_dh = invalid_entries_dh[["Site", "ID Cross", "Problem"]+saltos]

    # static replaces
    # => Cross Type
    #   - EXTERNO => Externo
    #   - INTERNO => Interno

    depara_cross_type_dict = {"EXTERNO": "Externo", "INTERNO": "Interno"}
    df["Tipo de Cross"] =  df['Tipo de Cross'].map(depara_cross_type_dict).fillna(df['Tipo de Cross'])

    df.to_excel(f"{pathImports}{site}/{site}_import.xlsx", index=False)
    invalid_entries_dh.to_excel(f"{pathImports}{site}/{site}_invalid_entries.xlsx", index=False)



