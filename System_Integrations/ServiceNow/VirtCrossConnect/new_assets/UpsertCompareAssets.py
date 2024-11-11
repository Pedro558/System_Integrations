import argparse
from System_Integrations.utils.parser import get_value
from commons.pandas.utils import *
from .Unveil import pathImports, sites, path as basePath



if __name__ == '__main__':
    
    for site in sites:
        df = get_df_from_excel(f"{pathImports}{site}/{site}_assets.xlsx")
        dfp = get_df_from_excel(f"{pathImports}{site}/{site}_assets_maritaca.xlsx")
        dfp_original = get_df_from_excel(f"{pathImports}{site}/{site}_assets_maritaca_original.xlsx")

        if df.empty or dfp.empty: continue

        df['Type'] = 'BEFORE'
        dfp['Type'] = 'AFTER'

        info_compare = pd.concat([df, dfp], ignore_index=True)
        info_compare = info_compare.sort_values(by=["ID Cross", "source"]).reset_index(drop=True)
        info_compare.to_excel(f"{pathImports}{site}/{site}_compare.xlsx")

        # compare with original answers 
        dfp['Type'] = 'AFTER'
        info_compare = pd.concat([df, dfp_original], ignore_index=True)
        info_compare = info_compare.sort_values(by=["ID Cross", "source"]).reset_index(drop=True)
        info_compare.to_excel(f"{pathImports}{site}/{site}_compare_original.xlsx")










