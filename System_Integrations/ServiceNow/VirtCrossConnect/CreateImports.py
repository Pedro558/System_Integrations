import os, traceback

from regex import B

from System_Integrations.ServiceNow.VirtCrossConnect.UpsertDepara import apply_de_para
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
        # if value == "DH03:T6:DG TI-M2 DIO.M2:PT9/10": breakpoint()
        if pd.isna(value):  # Skip NaN values
            return value
        
        parts = value.split(':')
        if len(parts) != 4: raise ''

        para = lookup_data_hall_dict.get(parts[0], parts[0])
        parts[0] = para if isinstance(para, str) else value  # Replace Data Hall part
        return ':'.join(parts)
        # if pattern.match(value):
        # else:
        #     return "[INVALID_FORMAT]=>"+value
    except:
        return "[INVALID_FORMAT]=>"+value
    
def replace_rack(value, lookup_rack):
    try:
        if pd.isna(value):  # Skip NaN values
            return value
        if pattern.match(value):
            # if value == "DH01:BL24:PP01:PT02": breakpoint()
            parts = value.split(':')
            dh = parts[0]
            rack = parts[1]
            para = lookup_rack[(lookup_rack["Data Hall"] == dh) & (lookup_rack["De"] == rack)]
            if para:
                breakpoint()
                parts[1] = para.values[0]

            return ':'.join(parts)
        else:
            return value
            return "[INVALID_FORMAT]=>"+value
    except:
        return value
    
def treat_virtual_dhs(df, config, list_of_dh):
    dh_field = config[0]
    rack_field = config[1]
    pp_field = config[2]
    port_field = config[3]
    comments_field = config[4]

    mask = df[dh_field].isin(list_of_dh)

    # df_pp = df.loc[mask, pp_field].astype(str)
    # df_port = df.loc[mask, df_port].astype(str)

    # # Update the 'Comments' column with 'Patch Panel' and 'Port'
    # df.loc[mask, comments_field] = 'Asset: ' + df_pp + '\nInterface: ' + df_port

    for idx in df[mask].index:
        pp_value = str(df.at[idx, pp_field])
        port_value = str(df.at[idx, port_field])
        rack_value = str(df.at[idx, rack_field])
        if (
            (pd.notna(pp_value) and pp_value not in ['', 'nan']) 
            or 
            (pd.notna(port_value) and port_value not in ['', 'nan'])
            or 
            (pd.notna(rack_value) and rack_value not in ['', 'nan'])
            ):

            # if df.at[idx, "ID Cross"] == "ID-POA1-00010": breakpoint()

            df.at[idx, comments_field] = 'Rack: ' + rack_value if rack_value != 'nan' else '' 
            df.at[idx, comments_field] += '\nAsset: ' + pp_value if pp_value != 'nan' else '' 
            df.at[idx, comments_field] += '\nInterface: ' + port_value if port_value != 'nan' else ''
                                        

    # Set 'Patch Panel' and 'Port' to blank
    df.loc[mask, [rack_field, pp_field, port_field]] = ''

    return df

sites = ["RJO1", "SPO1", "POA1", "CTA1", "BSB2", "BSB1"]
path = "C:/Users/filipe.uccelli/source/System_Integration/System_Integrations/ServiceNow/VirtCrossConnect/"
pathImports = f"{path}import/"

media_type_lookup = {
    "F0": "FO SM",
    "FO": "FO SM",
    "FO/UTP": "FO SM",
}

status_lookup = {
    "ATIVO": "Ativo"
}

columns_lookup = {
    "Data Hall2": "Data Hall",
    "Data de Ativação": "Data da Ativação",
    "Data Hall Ponta B2": "Data Hall Ponta B",
    "EXTERNO": "Tipo de Cross",
    "Numero Chamado": "Número Chamado",
    "Numero Chamado": "Número Chamado",
    "Numero Chamado": "Número Chamado"
}

virtual_dh = [
    "ESCRITÓRIO", # RJO1
    "SALA ELÉTRICA", # CTA1
    "SALA TELECOM - ESCRITÓRIO", # BSB1
    "SALA OPERAÇÃO", # BSB1 
    "SALA EQUATORIAL", # POA1
    "SALA INTERCONEXÃO (OI)", # POA1
    # "4º Andar", # POA1 - AVALIAR
    "SALA DE TRANSMISÃO", # POA1 - AVALIAR (Nossa sala? sala concentradora?)
    "SALA DE DADOS", # POA1 - AVALIAR (Nossa sala?) 
]

lookup_dh_sites = { # utilized to fix DH after custom verificarions
    "POA1": {
        "TC01": "POA1-3-TC01",
        "TC02": "POA1-3-TC01",
    }
}

# lookup_asset_sites = {
#     "POA1": {
#         "SOLTO": "",
#     }
# }
# 
# lookup_interface_site = {
#     "POA1": {
#         "SOLTO": "",
#     }
# }

# POA1 
# SE RACK CONTER => A* => TC01
# SE RACK CONTER => F* => SALA INTERCONEXÃO (OI)

cross_deactive = {
    "POA1": [
        "ID-POA1-00250",
        "ID-POA1-00253",
        "ID-POA1-00254",
        "ID-POA2-00271",
        "ID-POA2-00272",
        "ID-POA2-00282",
        "ID-POA1-00323",
        "ID-POA1-00352",
        "ID-POA1-00353",
        "ID-POA1-00354",
        "ID-POA1-00355",
        "ID-POA1-00383",
        "ID-POA1-00384",
        "ID-POA1-00386",
        "ID-POA1-00408",
    ]
}

cross_legado = {
    "POA1": [
        "ID-POA1-00015",
        "ID-POA1-00287",
    ],
    "RJO1": [
        "ID-RJO1-00009",
        "ID-RJO1-00013",
        "ID-RJO1-00100",
        "ID-RJO1-00101",
        "ID-RJO1-00104",
        "ID-RJO1-00119",
        "ID-RJO1-00120",
        "ID-RJO1-00121",
        "ID-RJO1-00122",
        "ID-RJO1-00123",
        "ID-RJO1-00124",
        "ID-RJO1-00138",
        "ID-RJO1-00281",
    ]
}

cross_bypass = {
    "SPO1": [
        ("ID-SPO1-00541", "Cliente (B) GLOBNET não encontrado"),
        ("ID-SPO1-00646", "Rack (A) BV23 dentro de data hall SPO1-1-DH01, não encontrado"),
        ("ID-SPO1-00647", "Rack (A) BV23 dentro de data hall SPO1-1-DH01, não encontrado"),
        ("ID-SPO1-01011", "Rack (B) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01015", "Rack (A) AL25 dentro de data hall SPO1-1-DH02, não encontrado"),
        ("ID-SPO1-01019", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01021", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01022", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01023", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado,"),
        ("ID-SPO1-01025", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01028", "Rack (A) AL28 A dentro de data hall SPO1-1-DH01, não encontrado,"),
        ("ID-SPO1-01036", "Rack (B) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01037", "Rack (B) AF18-A dentro de data hall SPO1-2-DH09, não encontrado,"),
        ("ID-SPO1-01041", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01042", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado,"),
        ("ID-SPO1-01047", "Rack (B) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01054", "Rack (B) AF18-A dentro de data hall SPO1-2-DH09, não encontrado,"),
        ("ID-SPO1-01063", "Rack (B) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01064", "Rack (B) AY36 dentro de data hall SPO1-1-DH03, não encontrado,"),
        ("ID-SPO1-01065", "Rack (B) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01033", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-01033", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00536", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00542", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00533", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00540", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00543", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00528", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00545", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00530", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00529", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00538", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00534", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00531", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00532", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00539", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00535", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00544", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00546", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00537", "Cliente (B) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00527", "Cliente (A) T-SYSTEMS DO BRASIL LTDA não encontrado"),
        ("ID-SPO1-00057", "Cliente (A) CM INDUSTRIA E COMERCIO LTDA não encontrado Cliente final CM INDUSTRIA E COMERCIO LTDA não encontrado"),
        ("ID-SPO1-00056", "Cliente (A) CM INDUSTRIA E COMERCIO LTDA não encontrado Cliente final CM INDUSTRIA E COMERCIO LTDA não encontrado"),
        ("ID-SPO1-00525", "Cliente (A) Dimension Data Brasil Tecnologia da Info não encontrado"),
        ("ID-SPO1-00523", "Cliente (A) Dimension Data Brasil Tecnologia da Info não encontrado"),
        ("ID-SPO1-00522", "Cliente (A) Dimension Data Brasil Tecnologia da Info não encontrado"),
        ("ID-SPO1-00524", "Cliente (A) Dimension Data Brasil Tecnologia da Info não encontrado"),
        ("ID-SPO1-01191", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01071", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01267", "Rack (A) AK59 B dentro de data hall SPO1-T-TC01, não encontrado"),
        ("ID-SPO1-01068", "Rack (B) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
        ("ID-SPO1-01268", "Rack (A) AK59 B dentro de data hall SPO1-T-TC01, não encontrado"),
        ("ID-SPO1-01190", "Rack (A) AF18-A dentro de data hall SPO1-2-DH09, não encontrado"),
    ],
    "POA1": [
        ("ID-POA1-00246", "data hall (B)  não encontrado"),
        ("ID-POA1-00317", "data hall (B)  não encontrado \nRack (A) AL40 dentro de data hall POA1-3-DH02, não encontrado"),
        ("ID-POA1-00249", "Rack (B) SOLTO dentro de data hall POA1-3-TC01, não encontrado"),
        ("ID-POA1-00242", "Cliente (A) E-SALES não encontrado \nCliente final E-SALES não encontrado"),
        ("ID-POA1-00466", "Cliente (A) E-SALES não encontrado \nCliente final E-SALES não encontrado"),
        ("ID-POA1-00238", "Cliente (A) E-SALES não encontrado \nCliente final E-SALES não encontrado"),
        ("ID-POA1-00443", "Cliente (A) E-SALES não encontrado \nCliente final E-SALES não encontrado"),
        ("ID-POA1-00145", "Cliente (A) E-SALES não encontrado \nCliente final E-SALES não encontrado"),
        ("ID-POA1-00164", "Cliente (A) E-SALES não encontrado \nCliente final E-SALES não encontrado"),
        ("ID-POA1-00013", "Rack (A) AK12 dentro de data hall POA1-1-DH01, não encontrado"),
        ("ID-POA1-00196", "Rack (A) AK12 dentro de data hall POA1-1-DH01, não encontrado"),
        ("ID-POA1-00011", "Rack (A) AOR25 dentro de data hall POA1-1-DH01, não encontrado"),
        ("ID-POA1-00111", "Rack (A) BJ15 dentro de data hall POA1-1-DH01, não encontrado"),
        ("ID-POA1-00501", "Cliente final FIERGS não encontrado"),
        ("ID-POA1-00498", "Cliente (B) IX BR (ESPELHAMENTO) não encontrado \n Rack (B) AL43.C dentro de data hall POA1-3-TC01, não encontrado"),
        ("ID-POA1-00480", "Rack (A) AZ22 dentro de data hall POA1-1-DH01, não encontrado"),
        ("ID-POA1-00323", ""),
        ("ID-POA1-00497", "Cliente (B) IX BR (ESPELHAMENTO) não encontrado \n Rack (B) AL43.C dentro de data hall POA1-3-TC01, não encontrado"),
        ("ID-POA1-00476", "Rack (A) AL36.B dentro de data hall POA1-3-TC01, não encontrado"),
        ("ID-POA1-00485", "Cliente (B) IX BR (ESPELHAMENTO) não encontrado \n Rack (B) AL43.C dentro de data hall POA1-3-TC01, não encontrado"),
        ("ID-POA1-00406", ""),
        ("ID-POA1-00493", "Cliente (B) IX BR (ESPELHAMENTO) não encontrado \n Rack (B) AL43.C dentro de data hall POA1-3-TC01, não encontrado"),
        ("ID-POA1-00494", "Cliente (B) IX BR (ESPELHAMENTO) não encontrado \n Rack (B) AL43.C dentro de data hall POA1-3-TC01, não encontrado"),
        ("ID-POA1-00460", "Cliente (B) IX BR (ESPELHAMENTO) não encontrado"),
        ("ID-POA1-00477", "Rack (A) AL36.B dentro de data hall POA1-3-TC01, não encontrado"),
        ("ID-POA1-00486", "Cliente (A) IX BR (ESPELHAMENTO) não encontrado \n Rack (A) AL43.C dentro de data hall POA1-3-TC01, não encontrado"),
        ("ID-POA1-00499", "Rack (A) AL36.B dentro de data hall POA1-3-TC01, não encontrado \n Rack (B) BN16.A dentro de data hall POA1-3-DH02, não encontrado"),
        ("ID-POA1-00459", "Cliente (B) IX BR (ESPELHAMENTO) não encontrado"),
        ("ID-POA1-00475", "data hall (B) TL01 não encontrado"),
        ("ID-POA1-00405", ""),
        ("ID-POA1-00496", "Cliente (B) IX BR (ESPELHAMENTO) não encontrado \n Rack (B) AL43.C dentro de data hall POA1-3-TC01, não encontrado"),
    ],
    "RJO1": [
        ("ID-RJO1-00017", ""),
        ("ID-RJO1-00019", ""),
        ("ID-RJO1-00016", ""),
        ("ID-RJO1-00015", ""),
        ("ID-RJO1-00018", ""),
        ("ID-RJO1-00136", "Rack (B) AK03 dentro de data hall RJO1-1-TC02, não encontrado"),
        ("ID-RJO1-00138", "Cliente (A) N/C não encontrado"),
        ("ID-RJO1-00222", "Rack (A) AN19 dentro de data hall RJO1-1-TC01, não encontrado \n Rack (B) AS07-A dentro de data hall RJO1-2-DH01, não encontrado"),
        ("ID-RJO1-00491", "Cliente (B) NEW TELECOM não encontrado"),
        ("ID-RJO1-00146", ""),
        ("ID-RJO1-00162", "Rack (A) TCO1 dentro de data hall RJO1-1-TR01, não encontrado"),
        ("ID-RJO1-00482", "Rack (A) AK13-B dentro de data hall RJO1-2-DH01, não encontrado"),
        ("ID-RJO1-00077", "Cliente (A) WLENET não encontrado"),
        ("ID-RJO1-00062", "Cliente (B) WLENET não encontrado \n Cliente final WLENET não encontrado"),
        ("ID-RJO1-00055", "Cliente (A) WLENET não encontrado"),
    ],
    "CTA1": [
        ("ID-CTA-00306", "Rack (B) BE31 B dentro de data hall CTA1-1-DH01, não encontrado"),
        ("ID-CTA-00225", "Cliente (A) UNI.CLOUD não encontrado \n Cliente final UNI.CLOUD não encontrado"),
        ("ID-CTA-00091", "Cliente (A) UNI.CLOUD não encontrado \n Cliente final UNI.CLOUD não encontrado"),
        ("ID-CTA-00092", "Cliente (A) UNI.CLOUD não encontrado \n Cliente final UNI.CLOUD não encontrado"),
        ("ID-CTA-00226", "Cliente (A) UNI.CLOUD não encontrado \n Cliente final UNI.CLOUD não encontrado"),
        ("ID-CTA-00283", "Cliente (A) UNI.CLOUD não encontrado \n Cliente final UNI.CLOUD não encontrado"),
        ("ID-CTA-00286", "Cliente (A) UNI.CLOUD não encontrado \n Cliente final UNI.CLOUD não encontrado"),
    ],
    "BSB1": [
        ("ID-BSB1-00356", "Rack (B) T6_SL1 dentro de data hall BSB1-SL-DH03, não encontrado"),
        ("ID-BSB1-00039", "Rack (B) SALA OPERAÇÃO dentro de data hall BSB1-SS-DH01, não encontrado"),
        ("ID-BSB1-00363", "Cliente (B) BR.DIGITAL não encontrado \n Rack (A) T0-01 dentro de data hall BSB1-SS-DH01, não encontrado"),
        ("ID-BSB1-00266", ""),
        ("ID-BSB1-00354", "Rack (B) T6_SL1 dentro de data hall BSB1-SL-DH03, não encontrado"),
        ("ID-BSB1-00355", "Rack (B) T4_SL1 dentro de data hall BSB1-SL-DH03, não encontrado"),
        ("ID-BSB1-00353", "Rack (B) T4_SL1 dentro de data hall BSB1-SL-DH03, não encontrado"),
    ],
    "BSB2": [
        ("ID-BSB2-00515", "Rack (B) F21RAO-S dentro de data hall BSB2-1-DH01, não encontrado"),
        ("ID-BSB2-00547", "Rack (A) F14RAW dentro de data hall BSB2-1-DH02, não encontrado"),
        ("ID-BSB2-00546", "Rack (A) F14RAQ dentro de data hall BSB2-1-DH02, não encontrado"),
        ("ID-BSB2-00538", "Rack (B) F2R2-S dentro de data hall BSB2-T-TC02, não encontrado"),
        ("ID-BSB2-00095", "Rack (B) F2R2-B dentro de data hall BSB2-T-TC03, não encontrado"),
        ("ID-BSB2-00539", "Rack (A) F2R2-S dentro de data hall BSB2-T-TC02, não encontrado"),
        ("ID-BSB2-00544", "Rack (B) F2R5 dentro de data hall BSB2-T-TC03, não encontrado"),
        ("ID-BSB2-00542", "Rack (B) F2R5 dentro de data hall BSB2-T-TC03, não encontrado"),
        ("ID-BSB2-00540", "Rack (A) F2R2-S dentro de data hall BSB2-T-TC02, não encontrado"),
        ("ID-BSB2-00511", "Rack (B) F2R5 dentro de data hall BSB2-T-TC03, não encontrado"),
        ("ID-BSB2-00533", "Rack (B) F2R2-B dentro de data hall BSB2-T-TC03, não encontrado"),
        ("ID-BSB2-00534", "Cliente (B) JET TELECOM-RD não encontrado"),
        ("ID-BSB2-00060", "Rack (B) F2RAQ dentro de data hall BSB2-1-DH01, não encontrado"),
        ("ID-BSB2-00062", "Rack (B) F2RAQ dentro de data hall BSB2-1-DH01, não encontrado"),
        ("ID-BSB2-00543", "Rack (B) F2R5 dentro de data hall BSB2-T-TC03, não encontrado"),
        ("ID-BSB2-00541", "Rack (B) F2R5 dentro de data hall BSB2-T-TC03, não encontrado"),
        ("ID-BSB2-00510", "Rack (B) F2R5 dentro de data hall BSB2-T-TC03, não encontrado"),
    ]
}


if __name__ == '__main__':
    lookup_customer_all = get_df_from_excel(pathImports+"_lookups/de_para_customer.xlsx", {"De": [], "Para": []})
    lookup_data_hall_all = get_df_from_excel(pathImports+"_lookups/de_para_data_hall.xlsx", {"De": [], "Para": []})
    lookup_rack_all = get_df_from_excel(pathImports+"_lookups/de_para_rack.xlsx", {"De": [], "Para": []})

    for site in sites:
        try:
            df = get_df_from_excel(f"{pathImports}/{site}/cross_{site}_data.xlsx")
            if df.empty: continue

            for column in df.columns:
                if column in columns_lookup.keys():
                    para = columns_lookup[column]
                    df[para] = df[column]
                    df = df.drop(columns=[column])

            lookup_customer = lookup_customer_all[lookup_customer_all["Site"] == site]
            lookup_data_hall = lookup_data_hall_all[lookup_data_hall_all["Site"] == site]
            lookup_rack = lookup_rack_all[lookup_rack_all["Site"] == site]

            df_import = get_df_from_excel(f"{pathImports}{site}_import.xlsx")

            df["Site"] = site
            saltos = [col for col in df.columns if col.startswith('Salto')]

            df["Tipo de Mídia"] = df["Tipo de Mídia"].map(media_type_lookup).fillna(df["Tipo de Mídia"])
            if "Status" in df.columns:
                df["Status"] = df["Status"].map(status_lookup).fillna(df["Status"])
            else:
                df["Status"] = "Ativo"
                
            # if site == "POA1": breakpoint(),
            list_deactive = cross_deactive.get(site)

            if list_deactive:
                df.loc[df["ID Cross"].isin(list_deactive), "Status"] = "Desativado"


            if "Legado" not in df.columns: df["Legado"] = ""
            list_legado = cross_legado.get(site)

            if list_legado: 
                df.loc[df["ID Cross"].isin(list_legado), "Legado"] = "SIM"

            # if "bypass" not in df.columns: df["bypass"] = ""
            df["bypass"] = "" 
            list_bypass = cross_bypass.get(site)
            if list_bypass:
                for x in list_bypass:
                    # try:
                    cross = df["ID Cross"] == x[0]
                    obs = df.loc[cross, "Observações Gerais"].iloc[0]
                    obs = str(obs)
                    obs = "" if obs == "nan" else ""
                    df.loc[cross, "Observações Gerais"] = obs + "\n" + x[1]
                    df.loc[cross, "bypass"] = "SIM"
                    # except Exception as e:
                    #     breakpoint()
        
            # use lookup to replace:,
            # => customer (Cliente Ponta A / Cliente Ponta B)")

            lookup_customer_dict = pd.Series(lookup_customer.Para.values, index=lookup_customer.De).to_dict()

            df['Cliente Ponta A'] = df['Cliente Ponta A'].str.strip()
            df['Cliente Ponta A'] = df['Cliente Ponta A'].map(lookup_customer_dict).fillna(df['Cliente Ponta A'])
            df['Cliente Ponta B'] = df['Cliente Ponta B'].str.strip()
            df['Cliente Ponta B'] = df['Cliente Ponta B'].map(lookup_customer_dict).fillna(df['Cliente Ponta B'])
            df['Cliente Final'] = df['Cliente Final'].str.strip()
            df['Cliente Final'] = df['Cliente Final'].map(lookup_customer_dict).fillna(df['Cliente Final'])

            # if site == "BSB1": breakpoint()")
            

            
            # => data hall (Data Hall / Data Hall Ponta B / Saltos),
            # saltos = ["Salto 1Salto 2Salto 3Salto 4Salto 5"]")


            lookup_data_hall_dict = pd.Series(lookup_data_hall.Para.values, index=lookup_data_hall.De).to_dict()
            df['Data Hall'] = df['Data Hall'].str.strip()

            df['Data Hall'] = df['Data Hall'].map(lookup_data_hall_dict).fillna(df['Data Hall'])
            df['Data Hall Ponta B'] = df['Data Hall Ponta B'].str.strip()

            df['Data Hall Ponta B'] = df['Data Hall Ponta B'].map(lookup_data_hall_dict).fillna(df['Data Hall Ponta B'])

            if site == "POA1":
                lookup = lookup_dh_sites.get(site)
                def fix_datahall(row, config):
                    dh_field = config[0]
                    rack_field = config[1]                    
                    mask = df[dh_field].isin(["TC01"])
                    for idx in df[mask].index:
                        if df.at[idx, dh_field] not in ["TC01"]:
                            df[dh_field] = df.at[idx, dh_field]

                        if str(df.at[idx, rack_field]).lower().startswith("f"):
                            df.at[idx, dh_field] = "SALA INTERCONEXÃO (OI)"
                        else:
                            df.at[idx, dh_field] = "TC01"



                fix_datahall(df, ("Data Hall", "Rack Ponta A"))
                fix_datahall(df, ("Data Hall Ponta B", "Rack Ponta B"))
                
                df['Data Hall'] = df['Data Hall'].map(lookup).fillna(df['Data Hall'])
                df['Data Hall Ponta B'] = df['Data Hall Ponta B'].map(lookup).fillna(df['Data Hall Ponta B'])



            invalid_entries_dh = pd.DataFrame(columns=df.columns)
            for salto in saltos:
                # df[salto] = df[salto].apply(lambda value: replace_data_hall(value, lookup_data_hall_dict)),
                processed_values = df[salto].apply(lambda value: replace_data_hall(value, lookup_data_hall_dict))
                processed_values = processed_values.fillna("")
                invalid_rows = processed_values[processed_values.notna() & processed_values.str.startswith("[INVALID_FORMAT]=>")]

                processed_values = processed_values.str.replace("[INVALID_FORMAT]=>", "")
                invalid_rows = invalid_rows.str.replace("[INVALID_FORMAT]=>", "")

                invalid_rows = df[df[salto].isin(invalid_rows)]
                # invalid_rows[salto] = invalid_rows[salto].str.replace("[INVALID_FORMAT]=>")")
                if not invalid_rows.empty:
                    invalid_rows = invalid_rows[["ID Cross", salto]]

                    invalid_entries_dh = pd.concat([invalid_entries_dh, invalid_rows])

                df[salto] = processed_values
                

            invalid_entries_dh["Site"] = site
            invalid_entries_dh["Problem"] = "INVALID FORMAT"
            invalid_entries_dh = invalid_entries_dh[["Site", "ID Cross", "Problem"]+saltos]

            # if site == "BSB1": breakpoint()")
            
            # => racks (Rack Ponta A / Rack Ponta B / Saltos),
            # lookup_rack_dict = pd.Series(lookup_rack.Para.values, index=lookup_rack.De).to_dict()")


            # old_df = df,
            # if site == "BSB2": breakpoint()")


            # Identificar cross onde DH a ou DB b seja uma das salas do virtual_df,
            # se sim, jogar patch panel e porta para campo comentario (comentario A ou comentario B - campos novos para esse cenario)")

            df["Comments A"] = ""
            config = ("Data Hall", "Rack Ponta A", "Patch Panel Ponta A", "Porta Ponta A", "Comments A")
            # if site == "POA1": breakpoint(),
            df = treat_virtual_dhs(df, config, virtual_dh)

            df["Comments B"] = ""
            config = ("Data Hall Ponta B", "Rack Ponta B", "Patch Panel Ponta B", "Porta Ponta B", "Comments B")
            # if site == "POA1": breakpoint()
            df = treat_virtual_dhs(df, config, virtual_dh)

            # if site == "POA1": breakpoint()
            df['Rack Ponta A'] = df['Rack Ponta A'].str.strip()
            df = apply_de_para(lookup_rack, df, 
                    match={"Site": "Site", "Data Hall": "Data Hall", "De": "Rack Ponta A"},
                    apply={"Para": "Rack Ponta A"}
                )
            df['Rack Ponta B'] = df['Rack Ponta B'].str.strip()
            df = apply_de_para(lookup_rack, df, 
                    match={"Site": "Site", "Data Hall": "Data Hall Ponta B", "De": "Rack Ponta B"},
                    apply={"Para": "Rack Ponta B"}
                )
                
            
            # df['Rack Ponta A'] = df['Rack Ponta A'].map(lookup_rack_dict).fillna(df['Rack Ponta A'])
            # df['Rack Ponta B'] = df['Rack Ponta B'].map(lookup_rack_dict).fillna(df['Rack Ponta B'])
            invalid_entries_rack = pd.DataFrame(columns=df.columns)
            for salto in saltos:
                processed_values = df[salto].apply(lambda value: replace_rack(value, lookup_rack))
                # invalid_rows = processed_values[processed_values.notna() & processed_values.str.startswith("[INVALID_FORMAT]=>")]
                # invalid_rows = invalid_rows.str.replace("[INVALID_FORMAT]=>")
                # invalid_rows = df[df[salto].isin(invalid_rows)]
                # Execução disso no data hall já levanta os saltos invalidos
                # if not invalid_rows.empty:
                #     invalid_rows["Site"] = site
                #     invalid_rows["Problem"] = "INVALID FORMAT"
                #     invalid_rows = invalid_rows[["SiteID CrossProblem", salto]]
                #     invalid_entries_rack = pd.concat([invalid_entries_rack, invalid_rows])

                df[salto] = processed_values


            # invalid_entries_dh = invalid_entries_dh[["SiteID CrossProblem"]+saltos]

            # if site == "BSB1": breakpoint()
            # static replaces
            # => Cross Type
            #   - EXTERNO => Externo
            #   - INTERNO => Interno

            depara_cross_type_dict = {"EXTERNO": "Externo", "INTERNO": "Interno"}
            df["Tipo de Cross"] =  df['Tipo de Cross'].map(depara_cross_type_dict).fillna(df['Tipo de Cross'])

            
            df.to_excel(f"{pathImports}{site}/{site}_import.xlsx", index=False)
            invalid_entries_dh.to_excel(f"{pathImports}{site}/{site}_invalid_entries.xlsx", index=False)


        except Exception as e:
            print(f"Error analyzing cross of site {site}")
            print(traceback.format_exc())
            print(e)

            

