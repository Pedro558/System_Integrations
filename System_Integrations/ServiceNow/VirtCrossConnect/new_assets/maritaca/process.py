import argparse
import maritalk, json
from System_Integrations.utils.parser import get_value
from commons.pandas.utils import *
from ..Unveil import pathImports, sites, path as basePath

instructions = """
Eu preciso padronizar os nomes, as interfaces e a classificação de uma série de ativos, o padrão irá variar dependendo do tipo do ativo:
Patch Panels: 
    - Classificação: Patch Panel
    - Interfaces: PT01, PT02, PT03 e etc
    - VOCE DEVE MANTER O NOME ORIGINAL DOS PATCH PANELS, NÃO ALTERE SUA NUMERAÇÃO
DIO:
    - Classificação: DIO
    - Nomes: DIO01, DIO02, DIO03, PP:FO (FO = Fibra óptica)
    - Interfaces: Extrair dos demais campos a informação de módulo ou slot, ao encontrar deve remove-la do campo de origem e inseri-la no campo interface da seguinte maneira:
        MODA/PT1-2, MODB/PT3-4 MOD1/PT1-2, MOD1/PT2-3, MOD2/PT4-5 e etc (Caso não haja a informação de módulo: MODX/PT1-2 e etc)
        Se na interface de um DIO houver apenas uma porta listada e não um par, deve-se tratar da seguinte maneira:
            - MOD1/PT1 => MOD1/PT1-2, MODB/PT5 => MODB/PT9-10 
        - MOD1/PT1 => MOD1/PT1-2, MODB/PT5 => MODB/PT9-10 
    - MOD1/PT1 => MOD1/PT1-2, MODB/PT5 => MODB/PT9-10 
    - VOCE DEVE MANTER O NOME ORIGINAL DOS DIO, NÃO ALTERE SUA NUMERAÇÃO
Classificados como Virtual:
    - Classificação:
        - DIO: se encontrar DIO no nome do ativo
        - Patch Panel: se o ativo for um patch panel da Elea
        - Virtual: se não se encaixar nas demais classificações e não for da Elea, classificar como virtual 
            (CASO ESTEJA CLASSIFICADO COMO VIRTUAL, APENAS PADRONIZAR O NOME DO ATIVO QUE ESTIVER DENTRO DO MESMO DATA HALL E RACK E POSSUIR ERROS DE DIGITAÇÃO)
        - Switch: se o ativo for um switch da Elea
            (CASO NÃO SEJA UM ATIVO DA ELEA, APENAS PADRONIZAR O NOME DO ATIVO QUE ESTIVER DENTRO DO MESMO DATA HALL E RACK E POSSUIR ERROS DE DIGITAÇÃO)
        - Router: se for um router da Elea
Classificados como Elea:
    - Cliente:
        - Se estiver classificado como Elea e o campo cliente estiver em branco, faça com que o propriedade cliente seja: ELEA DIGITAL INFRAESTRUTURA E REDES DE T
    - Classificação:
        - Switch: classificar como Switch caso encontre elementos como PSP, SW, SWITCH e etc no nome do equipamento (APENAS SE CLIENTE FOR ELEA, CASO CONTRARIO MANTER COMO VIRTUAL).
        - Router: classificar como Router caso encontre elementos como PRP, ROUTER e etc no nome do equipamento (APENAS SE CLIENTE FOR ELEA, CASO CONTRARIO MANTER COMO VIRTUAL).
        - Storage: classificar como Storage caso encontre elementos como STORAGE e etc no nome do equipamento. 
    - Nomes:
        - Caso seja um ACX da Elea: PRP-ELEAD-ACX-RJO1-01, PRP-ELEAD-ACX-RJO1-02, PRP-ELEAD-ACX-SPO1-01 e etc (APENAS SE CLIENTE FOR ELEA)
            (Caso não haja a informação de número: PRP-ELEAD-ACX-SPO1-XX e etc)
        - Caso seja um QFX da Elea: PSP-ELEAD-QFX-RJO1-01, PSP-ELEAD-QFX-RJO1-02, PSP-ELEAD-QFX-SPO1-01 e etc (APENAS SE CLIENTE FOR ELEA)
            (Caso não haja a informação de número: PSP-ELEAD-QFX-RJO1-XX e etc)
        - Demais: Padronizar nomes se encontrar mesmo ativo com nome ligeiramente diferente estando no mesmo data hall e rack (TODOS OS CLIENTES)
    - Interfaces:
        - Caso seja um ACX da Elea: et-0/0/1, et-0/0/2, et-0/0/3 e etc
        - Caso seja um QFX da Elea: ge-0/0/1, ge-0/0/2, ge-0/0/3 e etc

Considerações:
    - O unico campo vazio que pode ser preenchido é o Classificação (IMPORTANTE).
    - Caso o campo classificação esteja preenchido, você só pode altera-lo caso o cliente seja ELEA. OU se o cliente for outro, só pode alterar para virtual (QUANDO NECESSáRIO).
    - O Campo asset só pode ser modificado quando movimentado a informação de MOD OU SLOT para o campo interface, ou quando seguindo alguma regra descrita acima, no mais, mantenha ele intacto.
    - SEJA CONSISTENTE NAS TRATATIVAS, se vc aplicou uma tratativa para um asset virtual de mover a informação de MOD OU SLOT para o campo interface faça isso aos demais, NÃO trate parte dos dados de uma forma e a outra parte de outra. SEJA CONSISTENTE.
    
Abaixo está uma lista de exemplos de json antes e depois dos tratamentos corretos:
<JSON-EXEMPLOS>

Abaixo está uma lista de objetos json, eu quero que a resposta seja dada com a mesma lista, porém com as propriedades ajustadas seguintes as regras descritas acima.
Sua resposta deve conter apenas os dados em JSON, não me responta nada além disso.
Não indente a informação, nem response o literal "json" se ele não tiver correlação com os ajustes pedidos acima.
"""

instructions_new = """
Sanatize os dados abaixo.
Classifique em uma das opções:
    - DIO
    - Patch Panel
    - Switch
    - Router
    - Firewall

Padronize o nome dos Assets e as interfaces:
    - DIO: Nome da interface deve ser composto por modulo e porta. Caso essa informação não esteja presente na interface, procure no campo Asset.
            Se encontrar, remova a informação de modulo do outro campo e mantenha apenas na interface.
        ex.: MODA/PT1-2, MODB/PT3-4 MOD1/PT1-2, MOD1/PT2-3, MOD2/PT4-5 e etc (Caso não haja a informação de módulo: MODX/PT1-2 e etc)
    - Patch Panel: 
        ex.: PT01, PT02, PT03 e etc

Abaixo está uma lista de exemplos de json antes e depois dos tratamentos corretos:
<JSON-EXEMPLOS>

Abaixo está uma lista de objetos json, eu quero que a resposta seja dada com a mesma lista, porém com as propriedades ajustadas seguintes as regras descritas acima.
Sua resposta deve conter apenas os dados em JSON, não me responta nada além disso.
Não indente a informação, nem response o literal "json" se ele não tiver correlação com os ajustes pedidos acima.
"""


def get_token_count(data):
    instructions_count = maritalk.count_tokens(instructions+"\n")
    return maritalk.count_tokens(json.dumps(data)) + instructions_count

def divide_load(data, threashhold=30000):
    number_of_chunks = 3
    chunks = []
    while True:
        chunks = []
        chunk_size = len(data) // number_of_chunks
        remainder = len(data) % number_of_chunks

        for i in range(number_of_chunks):
            # Calculate start and end indices for the current chunk
            start = i * chunk_size + min(i, remainder)
            end = start + chunk_size + (1 if i < remainder else 0)
            chunks.append(data[start:end])
        
        surpased = False
        for chunk in chunks:
            token_count = maritalk.count_tokens(json.dumps(chunk))
            if token_count >= threashhold:
                number_of_chunks = number_of_chunks + 1
                surpased = True
                break

        if not surpased:
            break

    return chunks    

def execute_ai(data):
    model = maritalk.MariTalk(
        key="113741952737547612041_76e10ba99f7fd953",
        model="sabia-3"  # No momento, suportamos os modelos sabia-3, sabia-2-medium e sabia-2-small
    )

    instructions_count = maritalk.count_tokens(instructions)
    limit = 30000

    # the last value is to control the size of the chunks, the bigger the number, smaller the chunks, therefore more chunks
    # having more and smaller chunks is interesting to avoid losing data when the AI decides to do something weird
    threashold = limit - instructions_count - (25000) 
    # threashold = 200 # TEST

    responses = []
    chunks = divide_load(data, threashold)
    # breakpoint()
    # chunks = chunks[:8] # TEST

    for chunk in chunks:
        load = instructions+"\n"+json.dumps(chunk)
        messages = [
            {"role": "user", "content":load}
        ]

        response = ""
        for model_response_chunk in model.generate(
            messages,
            do_sample=True,
            max_tokens=threashold,
            temperature=0.7,
            top_p=0.95,
            stream=True,
            num_tokens_per_message=4
        ):
            response += get_value(model_response_chunk, lambda x: x["text"], "")
            print(response)

        responses.append(response)

    # breakpoint()
    new_data = []
    for index, response in enumerate(responses):
        try:
            response = response.replace("json", "")
            response = response.replace("\n", "")
            response = response.replace("```", "")
            new_data += json.loads(response)
        except:
            breakpoint()
            print("error on chunk response: ", index)

    return new_data


exemplo = pd.read_json(f"{basePath}/maritaca/maritaca_exemplo.json")
gabarito = pd.read_json(f"{basePath}/maritaca/maritaca_exemplo_gabarito.json")

if not (exemplo.empty and gabarito.empty):
    exemplo = exemplo.to_dict(orient='records')
    gabarito = gabarito.to_dict(orient='records')

    depara = []
    for ex in exemplo:
        gab = next((gab for gab in gabarito if gab["index"] == ex["index"]), None)
        if gab: depara.append((ex, gab))

    if depara:
        n = 1
        content = ""
        for dep in depara:
            titulo = f"Exemplo {n}:"
            content += f"{titulo} \n {json.dumps(dep[0])} => {json.dumps(dep[1])} \n\n"

        instructions = instructions.replace("<JSON-EXEMPLOS>", content)

def parse_file(pf, path, site):
    if pf == 'json':
        df = pd.read_json(f"{path}/{site}_assets_maritaca.json")
        df.to_excel(f"{path}/{site}_assets_maritaca.xlsx", index=True)
        df = pd.read_json(f"{path}/{site}_assets_maritaca_original.json")
        df.to_excel(f"{path}/{site}_assets_maritaca.xlsx_original", index=True)
    elif pf == 'xlsx':
        df = pd.read_excel(f"{path}/{site}_assets_maritaca.xlsx")
        df = df.to_dict(orient="records")
        with open(f"{path}/{site}_assets_maritaca.json", 'w', encoding='utf-8') as f:
            json.dump(df, f, ensure_ascii=False, indent=4)

        df = pd.read_excel(f"{path}/{site}_assets_maritaca_original.xlsx")
        df = df.to_dict(orient="records")
        with open(f"{path}/{site}_assets_maritaca_original.json", 'w', encoding='utf-8') as f:
            json.dump(df, f, ensure_ascii=False, indent=4)



def merge(df1, df2, how="right", on=["key"], apply_before_cleanup=lambda x:x):
    merged = pd.merge(df1, df2, how=how, on=on, suffixes=('', '_new'))
    merged = apply_before_cleanup(merged)

    for column in df2.columns:
        try:
            if column in df1.columns:
                merged[column] = merged[column + '_new'].combine_first(merged[column]) if column + '_new' in merged.columns else merged[column]
            else:
                merged[column] = merged[column + '_new'] if column + '_new' in merged.columns else merged[column]
        except Exception as e:
            breakpoint()

    merged = merged.loc[:, ~merged.columns.str.endswith('_new')] 
    return merged


def merge_outer_right(df_old, df_new, on=["key"]):
    # merged_right = merge(df_old, df_new, "right", on)
    # breakpoint()
    merged_outer_right = merge(df_old, df_new, "outer", on)
    return merged_outer_right


parser = argparse.ArgumentParser(description="process some flags.")
parser.add_argument('-s', '--site', type=str, help='site to perform the processing (uses the <site>_assets.json file)')
parser.add_argument('-y', action='store_true', default=False, help='process data no matter token count')
parser.add_argument('-pf', '--parsefile', type=str, help='"json" or "xlsx" the one informed will overwrite the other one')
parser.add_argument('-mf', action='store_true', default=False, help='merges the current maritaca file with the assets one')

if __name__ == '__main__':

    args = parser.parse_args()
    site = args.site
    args_y = args.y
    pf = args.parsefile
    mf = args.mf

    path = f"{pathImports}{site}"
    # pathfile = f"{path}/{site}_assets.json"
    pathFile = f"{path}/{site}_assets.json"


    if site not in sites:
        print(f"Site {site} not supported, must be one of: {', '.join(sites)}")
        exit()

    supported_pf = ['json', 'xlsx']
    if pf and pf.lower() not in supported_pf:
        print(f"Parse file option not supported, must be one of: {', '.join(supported_pf)}")
        exit()
    elif not site:
        print(f"To parse file, Site must be provided.")
        exit() 
    elif pf:
        msg = f"Are you sure you wanna the {pf} file to overwrite the other?"
        print(f"---> {msg} [Y/N]")
        awnser = "N"
        while (awnser := input("> ").upper()) not in ["Y", "N"]:
            print("Use [Y/N]")
        if awnser != "Y": exit()

        parse_file(pf, f"{pathImports}{site}", site)
        exit()
    
    columns_to_process = ["ID Cross", "Cliente", "Data Hall", "Rack", "Asset", "Interface", "Classificação", "index"]
    df_assets = get_df_from_json(pathFile, columns=[*columns_to_process, 'success'])
    df_assets = df_assets[df_assets['success'] == True]
    df = df_assets[columns_to_process]
    if df.empty:
        print(f"Not possible to get data from {pathFile}")
        exit()

    list_assets = df.to_dict(orient='records')

    if not list_assets:
        print(f"Not possible to extract JSON from {pathFile}")
        exit()

    already_ajusted = get_df_from_json(f"{path}/{site}_assets_maritaca.json")

    # used to keep track of maritaca original answers 
    original_already_ajusted = get_df_from_json(f"{path}/{site}_assets_maritaca_original.json")

    to_adjust_number = len(list_assets)
    adjusted_number = 0
    list_already_ajusted = already_ajusted.to_dict(orient='records')
    list_assets_to_treat = list_assets
    if not already_ajusted.empty:
        adjusted_number = len(list_already_ajusted)
        
        indexes_already_ajusted = [x["index"] for x in list_already_ajusted]
        list_assets_to_treat = [x for x in list_assets if x["index"] not in indexes_already_ajusted]

    adjusted_percentage = (adjusted_number / to_adjust_number) * 100
    adjusted_percentage = round(adjusted_percentage, 2)
    print(f"---> data treated {adjusted_percentage}% ({adjusted_number}/{to_adjust_number})")

    list_assets_to_treat_adjusted = [] 
    if list_assets_to_treat:
        # TEST
        # breakpoint()
        list_assets_to_treat = list_assets_to_treat[0:250]

        token_count = get_token_count(list_assets_to_treat)
        default_message = f"At least {token_count} tokens will be consumed to process this data."
        if not mf:
            if not args_y:
                print(f"---> {default_message} Proceed? [Y/N]")
                awnser = "N"
                while (awnser := input("> ").upper()) not in ["Y", "N"]:
                    print("Use [Y/N]")

                if awnser != "Y": exit()
            else:
                print("---> "+default_message)

            list_assets_to_treat_adjusted = execute_ai(list_assets_to_treat)

        else:
            list_assets_to_treat_adjusted = []


    # df_final = df_new_ajusted.combine_first(already_ajusted)
    df_new_ajusted = pd.json_normalize(list_assets_to_treat_adjusted)

    df_final = df_new_ajusted
    if df_final.empty: df_final = already_ajusted

    if not already_ajusted.empty:
        df_final["key"] = df_final["index"]
        already_ajusted["key"] = already_ajusted["index"]
        df_final = merge_outer_right(already_ajusted, df_final, on=["key"])
        df_final["index"] = df_final["index"].astype(int)

        if original_already_ajusted.empty: original_already_ajusted = df_final

        original_already_ajusted["key"] = original_already_ajusted["index"]
        already_ajusted["key"] = already_ajusted["index"]
        original_already_ajusted = merge_outer_right(already_ajusted, original_already_ajusted, on=["key"])
        original_already_ajusted["index"] = original_already_ajusted["index"].astype(int)

        original_already_ajusted = original_already_ajusted.drop(columns=["key"])
        df_final = df_final.drop(columns=["key"])

    def determine_asset_name(df):
        # In some cases, maritaca was changing the Patch Panel name wrongfully
        # this is to make sure the original PP name is used
        def _analyze(row):
            if 'Patch Panel' in [row['Classificação'], row['Classificação_new']]:
                matches = re.findall(r'^PP(\d+|[A-Z])$', str(row['Asset']))
                return row["Asset"] if matches else row["Asset_new"]

        df["Asset_new"] = df.apply(_analyze, axis=1) 
        return df

    # ===
    # Updates maritaca file
    # ===
    df = merge(df_assets, df_final, how='right', on=["index"], apply_before_cleanup=determine_asset_name)
    df = df.loc[:, ~df.columns.str.endswith('_new')]
    df["index"] = df["index"].astype(int)

    with open(f"{path}/{site}_assets_maritaca.json", 'w', encoding='utf-8') as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=4)

    with open(f"{path}/{site}_assets_maritaca_original.json", 'w', encoding='utf-8') as f:
        json.dump(original_already_ajusted.to_dict(orient="records"), f, ensure_ascii=False, indent=4)

    # df = pd.json_normalize(list_assets_adjusted)
    df.to_excel(f"{path}/{site}_assets_maritaca.xlsx", index=False)
    original_already_ajusted.to_excel(f"{path}/{site}_assets_maritaca_original.xlsx", index=False)
    

    # ===
    # Assets: on match update, keep old ones
    # === 
    merged_df = pd.merge(df_assets, df_final, on='index', how='outer', suffixes=('_df1', '_df2'))

    if "Classificacao" in df_final.columns: del df_final["Classificacao"]
    if "Classificacao" in merged_df.columns: del merged_df["Classificacao"]

    columns_to_clean_up = [x for x in df_final.columns if x not in ["index"]]
    for column in columns_to_clean_up:
        if column in ["index"]: continue
        merged_df[column] = merged_df[f'{column}_df2'].combine_first(merged_df[f'{column}_df1'])

    merged_df = merged_df.drop(columns=[f'{column}_df2' for column in columns_to_clean_up] + [f'{column}_df1' for column in columns_to_clean_up])
    merged_df.loc()

    with open(f"{path}/{site}_assets.json", 'w', encoding='utf-8') as f:
        json.dump(merged_df.to_dict(orient="records"), f, ensure_ascii=False, indent=4)

    # df = pd.json_normalize(list_assets_adjusted)
    # breakpoint()
    merged_df.to_excel(f"{path}/{site}_assets.xlsx", index=False)