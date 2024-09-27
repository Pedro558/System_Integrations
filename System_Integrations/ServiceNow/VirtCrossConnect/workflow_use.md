
# Step 1: Sanitizing Data

## 1. Getting the data
The initial data was filled in excel files and are in the elea sharepoint.

Get in contact with the data center supervisor to get the data.

## 2. Determining lookups
With the data at hand, you need to insert the xlsx inside that path: `import/<SITE>/cross_<SITE>_data.xlsx`. 

Be sure to rename the file to the one described above. 

Then run the script "UpsertDepara". You can run it like so:

```bash
python -m System_Integrations.ServiceNow.VirtCrossConnect.UpsertDepara
```

Be sure to update the variable inside this script that points to the file.

This lookup file will be used to map incorrect Customer, Data Hall and racks into the ones registered in ServiceNow. 

(During the process this was filled by the data hall operators)

## 3. Creating the import file
With the lookup files mapped, you can run the script "CreateImports":

```bash
python -m System_Integrations.ServiceNow.VirtCrossConnect.CreateImports
```

This will generate a file `<SITE>_import.xlsx` and a file `<SITE>_invalid_entries.xlsx`. 

The latter contains Hops that were not in the correct format.

## 4. Importing the file into ServiceNow
I would usually copy the files and save them in another directory and organize them by import tries (folders like: "DEV/import_1", "DEV/import_2", "PRD/import_1").

- Search ServiceNow for "Load Data"
- Select the import file and submit
- Select Run Transformation
- Select `u_import_cross_connect_validations` (This is a script that checks for errors)
- Run transformation
- The import will be done and an Import set number will be shown to you
- Open the import log table and filter by the import set
- Export the table as excel
- Put the file inside the `import/<SITE>/` directory
- Rename the file to `<SITE>_import_result.xlsx`

## 5. Generating the report file
With the `import/<SITE>/<SITE>_import_result.xlsx`, now run:

```bash
python -m System_Integrations.ServiceNow.VirtCrossConnect.UpsertReport
```

This will generate the file: `<SITE>_excecoes.xlsx`.

With this file, I do a meeting with the data hall operators and discuss the errors.

## 6. Repeat the process
Repeat the process until all the errors are resolved.

<br>
<br>
<br>

# Step 2: Creating the new structure

Up to this point, were inserted the cross connect data into the old table cross connect table inside ServiceNow.

Now we will take this sanitized data and break it down into assets and connect them with wire instances.

#### All this process will be inside the folder `new_assets`

## 1. Getting the data

- Search ServiceNow for Cross Connect (u_cmdb_ci_cross_connect)
- Filter by site, and export them as excels
- Place the files at `import_data/<SITE>/cross_<SITE>_data.xlsx` 

## 2. Unveil the assets

Run: 
```bash
python -m System_Integrations.ServiceNow.VirtCrossConnect.new_assets.Unveil
```

This will create a file `<SITE>_assets.xlsx`

The script gathered the info from "Side A", "Side B" and Hops, and uniformed the data as a list of objects.

## 3. Using AI

We will run this data through a AI model alongside the instructions to sanatize it.

Run:
```bash
python -m System_Integrations.ServiceNow.VirtCrossConnect.new_assets.maritaca.process -s <SITE>
```

(Or another model if it is implemented)

This will create a file `<SITE>_assets_maritaca.json` and `<SITE>_assets_maritaca.xlsx`

Use the xlsx to better visualize the new data, but any adjustment should be done to the .json file

