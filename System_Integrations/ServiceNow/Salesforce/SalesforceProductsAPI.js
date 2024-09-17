default_behavior = {
    "self": {
        "op": "get_all"
    },
    "cmdb_ci_service_business": {
        "op": "get",
        "fields": ["company", "location", "u_delivery_request.request.number"]
    },
    "others": {
        "op": "ignore"
    }
};

table_field_mapping = {
    "u_cmdb_ci_colocation": {
        "self": {
            "op": "get",
            "fields": ["number", "u_rack", "u_rack_size", "u_dc_load"]
        }
    },
    "u_cmdb_bs_ci_cage": {
        "self": {
            "op": "get",
            "fields": ["number", "u_rack_quantity", "u_dc_load"]
        }
    },
    "u_cmdb_ci_transceiver": {
        "self": {
            "op": "get",
            "fields": ["number", "u_band", "u_model_t"]
        }
    },
    "u_cmdb_ci_static_switch": {
        "self": {
            "op": "get",
            "fields": ["u_rack", "u_position"]
        }
    },
    "u_cmdb_ci_smart_hands": {
        "self": {
            "op": "get",
            "fields": ["u_horas_mensais"]
        }
    },
    "u_cmdb_ci_switch_tor": {
        "self": {
            "op": "get",
            "fields": ["u_rack", "u_kit", "u_model_s"]
        }
    }
};


function find_tables(req) {
    tableNames = [];

    for (table in table_field_mapping) {
        gs.print(table)
        if (table == "self" || table == "others") continue;

        var gr = new GlideRecord(table);
        gr.initialize()
        gr.addQuery("u_delivery_request.request.number", req)
        // gr.AddEncodedQuery("u_delivery_request.request.number="+req);
        gr.query();
        
        if (gr.next()) {
            tableNames.push(table);
        }

    }

    return tableNames;
}


function get_fields(tableName) {
    mapping = table_field_mapping[tableName] ? table_field_mapping[tableName] : {};
    for (prop in default_behavior) {
        mapping[prop] = mapping[prop] || default_behavior[prop];
    }

    if (!mapping) throw tableName + ' is not a valid product option';

    var tableUtil = new TableUtils(tableName);
    var parentTables = tableUtil.getTables().toArray();

    var parentColumns = [];
    for (var i = 0; i < parentTables.length; i++) {
        var table = parentTables[i];

        parentConfig = mapping[table] ? mapping[table] : 
                        table == tableName ? mapping["self"] :
                        mapping["others"];
        
                        
        if (!parentConfig) {
            parentConfig = default_behavior[table] ? default_behavior[table] : 
                            table == tableName ? default_behavior["self"] :
                            default_behavior["others"];
        }

        

        ignore = parentConfig.op == "ignore" || !parentConfig.op;
        if (ignore) continue;

        
        var grSysParent = new GlideRecord('sys_dictionary');
        grSysParent.addEncodedQuery('name=' + table + '^internal_type!=collection^internal_typeISNOTEMPTY');
        grSysParent.addOrderBy('column_label');
        grSysParent.query();
        
        tableColumns = [];
        while (grSysParent.next()) tableColumns.push(grSysParent.element.toString());
        
        fields_treated = parentConfig.fields.map(function(e) { return e.split('.')[0]; });
        function map_get (e) {
            index = fields_treated.indexOf(e);
            // gs.print(e + ' ' + index)

            if (index > -1) return parentConfig.fields[index];
        }
        function map_remove (e) {
            index = fields_treated.indexOf(e);
            if (index == -1) return e;
        }

        tableColumns = parentConfig.op == "get_all" ? tableColumns :
            parentConfig.op == "get" ? tableColumns.map(map_get) :
            parentConfig.op == "remove" ? tableColumns.map(map_remove) : [];

        finalFields = []
        for (var j = 0; j < tableColumns.length; j++) {
            field = tableColumns[j];
            if (field) finalFields.push(field)
        }
        

        parentColumns = parentColumns.concat(finalFields);
    }

    return parentColumns;
}


function get_data(tableName, fields, req) {
    var gr = new GlideRecord(tableName);
    gr.initialize()
    gs.print("SEARCHING TABLE "+ tableName + " u_delivery_request.request.number="+req);
    gr.addQuery("u_delivery_request.request.number", req)
    // gr.AddEncodedQuery("u_delivery_request.request.number="+req);
    
    gr.query();
    if (!gr.next()) return null;

    var obj = {};
    for (var i=0; i<fields.length; i++) {
        field = fields[i];
        obj[field] = gr.getDisplayValue(field);
    }

    gs.print("FOUND" + JSON.stringify(obj))
    return obj;
}

(function process(/*RESTAPIRequest*/ request, /*RESTAPIResponse*/ response) {
	var req = request.queryParams.request_number;

	tableNames = find_tables(req);
    results = [];
    for (var i = 0; i < tableNames.length; i++) {
        tableName = tableNames[i];
        fields = get_fields(tableName);
        result = get_data(tableName, fields, req);
        if (result) results.push(result);
    }
	
	// Set the response body
    var responseBody = JSON.stringify(results);
 
    // Write the response using the response stream
    response.setContentType('application/json');
    response.getStreamWriter().writeString(responseBody);
})(request, response);

// EXAMPLE OF USE
// req = "REQ0023301"
// tableNames = find_tables(req);
// gs.print("TABLE NAMES "+tableNames);

// results = [];
// for (var i = 0; i < tableNames.length; i++) {
//     tableName = tableNames[i];
//     gs.print("Getting fields of "+tableName);
//     fields = get_fields(tableName);
//     gs.print("Looking for products related to "+req);
//     result = get_data(tableName, fields, req);
//     if (result) results.push(result);
// }

// gs.print("ALL OBJS: " + JSON.stringify(results));
