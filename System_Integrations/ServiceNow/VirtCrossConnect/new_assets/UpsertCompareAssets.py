import argparse
from System_Integrations.utils.parser import get_value
from commons.pandas.utils import *
from .Unveil import pathImports, sites, path as basePath



if __name__ == '__main__':
    
    for site in sites:
        df = get_df_from_excel(f"{pathImports}{site}/{site}_assets.xlsx")
        dfp = get_df_from_excel(f"{pathImports}{site}/{site}_assets_maritaca.xlsx")

        if df.empty or dfp.empty: continue

        df['Type'] = 'BEFORE'
        dfp['Type'] = 'AFTER'

        info_compare = pd.concat([df, dfp], ignore_index=True)
        info_compare = info_compare.sort_values(by=["ID Cross", "source"]).reset_index(drop=True)

        info_compare.to_excel(f"{pathImports}{site}/{site}_compare.xlsx")

        # df_dict = df.to_dict(orient="records")
        # dfp_dict = dfp.to_dict(orient="records")

        # info_compare = []
        # for row in df_dict:
        #     match_item = lambda a,b : a['Id Cross'] == b['Id Cross'] and a['source'] == b['source']
        #     matching = next((x for x in dfp_dict if match_item(x, row)), None)

        #     if matching: 
        #         info_compare.append()








