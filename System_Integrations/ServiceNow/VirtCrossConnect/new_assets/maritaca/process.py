import argparse
import maritalk, json
from System_Integrations.utils.parser import get_value
from commons.pandas.utils import *
from ..Unveil import pathImports, sites, path as basePath

instructions = """
Eu preciso padronizar os nomes, as interfaces e a classificação de uma série de ativos, o padrão irá variar dependendo do tipo do ativo:
Patch Panels: 
    - Classificação: Patch Panel
    - Nomes: PP01, PP02, PP03 e etc
    - Interfaces: PT01, PT02, PT03 e etc
DIO:
    - Classificação: DIO
    - Nomes: DIO01, DIO02, DIO03 e etc
    - Interfaces: Extrair dos demais campos a informação de módulo ou slot, ao encontrar deve remove-la do campo de origem e inseri-la no campo interface da seguinte maneira:
        MODA/PT1-2, MODB/PT3-4 MOD1/PT1-2, MOD1/PT2-3, MOD2/PT4-5 e etc (Caso não haja a informação de módulo: MODX/PT1-2 e etc)
        Se na interface de um DIO houver apenas uma porta listada e não um par, deve-se tratar da seguinte maneira:
            - MOD1/PT1 => MOD1/PT1-2, MODB/PT5 => MODB/PT9-10 
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
    number_of_chunks = 1
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

def parse_file(path, site):
    df = pd.read_json(f"{path}/{site}_assets_maritaca.json")
    df.to_excel(f"{path}/{site}_assets_maritaca.xlsx")

def merge(df1, df2, how="right", on=["key"]):
    merged = pd.merge(df1, df2, how=how, on=on, suffixes=('', '_new'))
    for column in df2.columns:
        if column in df1.columns:
            merged[column] = merged[column + '_new'].combine_first(merged[column]) if column + '_new' in merged.columns else merged[column]
        else:
            merged[column] = merged[column + '_new'] if column + '_new' in merged.columns else merged[column]

    merged = merged.loc[:, ~merged.columns.str.endswith('_new')] 
    return merged


def merge_outer_right(df_old, df_new, on=["key"]):
    merged_right = merge(df_old, df_new, "right", on)
    merged_outer_right = merge(merged_right, df_new, "outer", on)
    return merged_outer_right


parser = argparse.ArgumentParser(description="process some flags.")
parser.add_argument('-s', '--site', type=str, help='site to perform the processing (uses the <site>_assets.json file)')
parser.add_argument('-y', action='store_true', default=False, help='process data no matter token count')
parser.add_argument('-pf', action='store_true', default=False, help='parses existing processed json file to xlsx')

if __name__ == '__main__':

    args = parser.parse_args()
    site = args.site
    args_y = args.y
    pf = args.pf

    path = f"{pathImports}{site}"
    # pathfile = f"{path}/{site}_assets.json"
    pathFile = f"{path}/{site}_assets.json"


    if site not in sites:
        print(f"Site {site} not supported, must be one of: {', '.join(sites)}")
        exit()

    if pf:
        parse_file(path, site)
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

    if not list_assets_to_treat: exit()


    # TEST
    list_assets_to_treat = list_assets_to_treat[0:1]



    token_count = get_token_count(list_assets_to_treat)
    default_message = f"At least {token_count} tokens will be consumed to process this data."
    if not args_y:
        print(f"---> {default_message} Proceed? [Y/N]")
        awnser = "N"
        while (awnser := input("> ").upper()) not in ["Y", "N"]:
            print("Use [Y/N]")

        if awnser != "Y": exit()
    else:
        print("---> "+default_message)

    
    list_assets_to_treat_adjusted = execute_ai(list_assets_to_treat)

    # df_final = df_new_ajusted.combine_first(already_ajusted)
    df_new_ajusted = pd.json_normalize(list_assets_to_treat_adjusted)

    df_final = df_new_ajusted
    if not already_ajusted.empty:
       df_final["key"] = df_final["index"]
       already_ajusted["key"] = already_ajusted["index"]
       df_final = merge_outer_right(already_ajusted, df_final, on=["key"])
       df_final["index"] = df_final["index"].astype(int)
       df_final = df_final.drop(columns=["key"])
       # merged_right = pd.merge(already_ajusted, df_new_ajusted, how='right', on=['key'], suffixes=('', '_new'))
       # for column in df_new_ajusted.columns:
       #     if column in already_ajusted.columns:
       #         merged_right[column] = merged_right[column + '_new'].combine_first(merged_right[column]) if column + '_new' in merged_right.columns else merged_right[column]
       #     else:
       #         merged_right[column] = merged_right[column + '_new'] if column + '_new' in merged_right.columns else merged_right[column]

       # merged_right = merged_right.loc[:, ~merged_right.columns.str.endswith('_new')] 

       # df_final = already_ajusted
       # df_final = df_final.merge(merged_right, on=['key'], how='outer', suffixes=('', '_new'))
       # for column in df_new_ajusted.columns:
       #     if column in already_ajusted.columns:
       #         df_final[column] = df_final[column + '_new'].combine_first(df_final[column]) if column + '_new' in df_final.columns else df_final[column]
       #     else:
       #         df_final[column] = df_final[column + '_new'] if column + '_new' in df_final.columns else df_final[column]

       # df_final = df_final.loc[:, ~df_final.columns.str.endswith('_new')]
       # df_final["index"] = df_final["index"].astype(int)
       # df_final = df_final.drop(columns=["key"])

    df = merge(df_assets, df_final, how='right', on=["index"])
    # df = df_assets.merge(df_final, how="right", on=["index"], suffixes=('', '_new'))
    # for column in df_assets.columns:
    #     if column in df.columns:
    #         df[column] = df[column + '_new'].combine_first(df[column]) if column + '_new' in df.columns else df[column]
    #     else:
    #         df[column] = df[column + '_new'] if column + '_new' in df.columns else df[column]

    df = df.loc[:, ~df.columns.str.endswith('_new')]
    df["index"] = df["index"].astype(int)

    with open(f"{path}/{site}_assets_maritaca.json", 'w', encoding='utf-8') as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=4)

    # df = pd.json_normalize(list_assets_adjusted)
    df.to_excel(f"{path}/{site}_assets_maritaca.xlsx", index=False)