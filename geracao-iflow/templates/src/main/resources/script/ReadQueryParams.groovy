import com.sap.gateway.ip.core.customdev.util.Message

/*
 * Lê a query string de um GET (header CamelHttpQuery) e grava uma exchange property
 * qp_<nome> para cada parâmetro, com URL decoding.
 * Obrigatório em todo iFlow HTTPS GET: consulta usa query params (?chave=valor), não body
 * JSON e não path extra após o urlPath do sender.
 * Motivo do Groovy: o HTTPS sender entrega a query inteira em um único header e não existe
 * processor nativo que a divida em pares chave/valor.
 * Entrada : header CamelHttpQuery (ex.: customerId=123&from=2025-01-01 ou cep=01001000)
 *           property p_requiredParams (opcional, lista separada por vírgula)
 * Saída   : properties qp_customerId, qp_from, qp_cep, ...
 *           erro IllegalArgumentException se faltar parâmetro obrigatório
 */
Message processData(Message message) {
    String query = (message.getHeaders().get("CamelHttpQuery") as String) ?: ""
    Map<String, String> params = [:]

    query.split("&").each { String pair ->
        if (!pair) return
        int idx = pair.indexOf("=")
        String key = idx >= 0 ? pair.substring(0, idx) : pair
        String value = idx >= 0 ? pair.substring(idx + 1) : ""
        key = URLDecoder.decode(key, "UTF-8")
        value = URLDecoder.decode(value, "UTF-8")
        if (key) {
            params[key] = value
        }
    }

    params.each { String key, String value ->
        message.setProperty("qp_" + key, value)
    }

    String required = (message.getProperty("p_requiredParams") as String) ?: ""
    List<String> missing = required.split(",")
        .collect { it.trim() }
        .findAll { it && !params.containsKey(it) }
    if (missing) {
        throw new IllegalArgumentException("Parâmetro(s) obrigatório(s) ausente(s): " + missing.join(", "))
    }

    return message
}
