// This script is run inside snow, more specifically in the 
// import set that maps the values from the exel to the cross table

function get_customer(customerName) {
	var customer = new GlideRecord("customer_account");
	customer.addQuery("name", customerName);
	customer.query();

	return customer.next();
}

function get_data_hall(dataHallName) {
	var datahallGR = new GlideRecord("u_cmdb_ci_data_hall");
	datahallGR.addQuery("name", dataHallName);
	datahallGR.query();

	return datahallGR.next();
}

function get_rack(rackName, dataHallName, customerName) {
	var rackGR = new GlideRecord("cmdb_ci_rack");
	// rackGR.addQuery("name", rackName);
	// rackGR.addQuery("u_data_hall.name", dataHallName);
	// rackGR.addQuery("company.name", customerName);
	rackGR.addEncodedQuery("nameSTARTSWITH"+rackName+
							"^u_data_hall.nameSTARTSWITH"+dataHallName+
							"^company.nameSTARTSWITH"+customerName+
							"^ORcompanyISEMPTY"
							);
	rackGR.query();

	racksFound = [];
	while (rackGR.next())
		racksFound.push(rackGR);
	
	return racksFound;
}


(function transformRow(source, target, map, log) {
	ignore = false;

	try {
		var cross_id = source.u_id_cross;
		var errors = [];

		var crossGR = new GlideRecord("u_cmdb_ci_cross_connect");
		crossGR.addQuery("name", cross_id);
		crossGR.query();

		// check if cross exists
		if (crossGR.next()) {
			ignore = true;
			return null; //throw "ID CROSS "+cross_id+" já cadastrado: "+crossGR.sys_id;
		}

		// check if customer exists (A)
		customerA = get_customer(source.u_cliente_ponta_a);
		if (!customerA) errors.push("Cliente (A) "+source.u_cliente_ponta_a+" não encontrado");
		
		// check if customer exists (B)
		customerB = get_customer(source.u_cliente_ponta_b);
		if (!customerB) errors.push("Cliente (B) "+source.u_cliente_ponta_b+" não encontrado");

		datahallA = get_data_hall(source.u_data_hall);
		if (!datahallA) errors.push("data hall (A) "+source.u_data_hall+" não encontrado"); 

		datahallB = get_data_hall(source.u_data_hall_ponta_b);
		if (!datahallB) errors.push("data hall (B) "+source.u_data_hall_ponta_b+" não encontrado");

		// check if rack inside data hall exists (A) 
		racksFound = get_rack(source.u_rack_ponta_a, source.u_data_hall, source.u_cliente_ponta_a);
		if (!racksFound || racksFound.lengh == 0) errors.push("Rack (A) "+source.u_rack_ponta_a+" dentro de data hall "+source.u_data_hall+" de cliente "+source.u_cliente_ponta_a+", não encontrado");
		if (racksFound.lengh > 1) {
			errors.push("Mais de um Rack foi detectado para combinação (A) : Rack "+source.u_rack_ponta_a+", Data hall "+source.u_data_hall+", Cliente"+source.u_cliente_ponta_a);
		}
		target.u_rack_ponta_a = racksFound[0].sys_id;

		// check if rack inside data hall exists (B)
		racksFound = get_rack(source.u_rack_ponta_b, source.u_data_hall_ponta_b, source.u_cliente_ponta_b);
		if (!racksFound || racksFound.lengh == 0) errors.push("Rack (B) "+source.u_rack_ponta_b+" dentro de data hall "+source.u_data_hall_ponta_b+" de cliente "+source.u_cliente_ponta_b+", não encontrado");
		if (racksFound.lengh > 1) {
			errors.push("Mais de um Rack foi detectado para combinação (B) : Rack "+source.u_rack_ponta_b+", Data hall "+source.u_data_hall_ponta_b+", Cliente"+source.u_cliente_ponta_b);
		}

		if (errors.length > 0) throw errors;

		target.u_rack_ponta_b = racksFound[0].sys_id;

	}
	catch(error) {
		errors = error.join("\n");
		log.error(source.u_id_cross+" => \n"+ errors);
		ignore = true;
	}

})(source, target, map, log, action==="insert");