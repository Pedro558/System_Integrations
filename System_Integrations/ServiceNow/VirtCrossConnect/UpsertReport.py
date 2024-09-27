import os

from pandas import DataFrame

from commons.pandas.utils import *

from System_Integrations.auth.api_secrets import get_api_token
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from dotenv import load_dotenv

pattern = re.compile(r'^[A-Za-z0-9\-]+:[A-Za-z0-9\-]+:[A-Za-z0-9\-]+:[A-Za-z0-9\-\\\/]+$')

sites = ["RJO1", "SPO1", "POA1", "CTA1", "BSB2", "BSB1"]
path = "C:/Users/filipe.uccelli/source/System_Integration/System_Integrations/ServiceNow/VirtCrossConnect/"
pathImports = f"{path}import/"

columns = ["Import set", "ID Cross", "Problemas", "Classificação", "Status", "Tratativa", "Observação"]

for site in sites:
    df = get_df_from_excel(f"{pathImports}{site}/{site}_import_result.xlsx")
    df_report = get_df_from_excel(f"{pathImports}{site}/{site}_excecoes.xlsx", columns=columns)
    if df.empty: continue

    # df_report = DataFrame(columns=columns)

    df['Import set'] = df['Import set'].astype(str)

    if not df_report.empty:
        df_report['Import set'] = df_report['Import set'].astype(str)

    df[["ID Cross", "Problemas"]] = df["Message"].str.split("=> \n", expand=True)

    # merged_df = df_report.merge(df, on=['ID Cross', 'Problemas'], how="left", suffixes=["", "_new"])
    # merged_df = merged_df.drop_duplicates(subset=['Import set', 'ID Cross', "Problemas_new"])
    # merged_df = merged_df.reset_index()
    # merged_df['Import set'] = merged_df['Import set_new'].combine_first(df['Import set'])

    def concat_unique(import_sets):
        # if site == "BSB1": breakpoint()
        unique_items = list(set(import_sets))
        return ','.join(sorted(set(unique_items)))


    merged_df = pd.concat([df_report, df], ignore_index=True)
    # merged_df['Import set'] = merged_df.groupby(['ID Cross', 'Problemas'])['Import set'].transform(lambda x: ','.join(sorted(set(x))))
    merged_df['Import set'] = merged_df.groupby(['ID Cross', 'Problemas'])['Import set'].transform(concat_unique)
    merged_df = merged_df.drop_duplicates(subset=['ID Cross', 'Import set', 'Problemas'], keep='first')

    # merged_df = pd.merge(df, df_report, on=['Import set', 'ID Cross', 'Problemas'], suffixes=('_df1', '_df2'), how='outer')
    final_df = merged_df[columns]
    # final_df.columns = columns
    # if site == "BSB2": breakpoint()
    final_df.to_excel(f"{pathImports}{site}/{site}_excecoes.xlsx", index=False)