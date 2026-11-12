import com.sap.gateway.ip.core.customdev.util.Message
import groovy.json.JsonSlurper
import java.io.InputStream
import java.io.Reader

/*
 * Valida campos obrigatorios de um JSON pass-through e grava p_payloadValido.
 * Motivo do Groovy: JSON to XML + Router XPath apos sender HTTPS falha com
 * InvalidXPathException + SAXParseException mesmo com Content Modifier reescrevendo o body.
 * Usar quando o receiver recebe o mesmo JSON (sem Message Mapping, XSLT ou Filter).
 * Entrada : property p_bodyOriginal (String, byte[] ou stream). Se vazia, getBody(String) e getBody(InputStream).
 * Saida   : p_bodyOriginal (String), p_payloadValido ("true"/"false", nunca Boolean), p_mensagemValidacao
 *
 * Ajuste as listas cabecalho e itens. itens = null desliga a checagem de array.
 */
Message processData(Message message) {
    List<String> cabecalho = ["campoObrigatorio"]
    String nomeArray = "itens"
    List<String> camposItem = ["id"]

    String json = materializar(message)
    String mensagem = validar(json, cabecalho, nomeArray, camposItem)
    if (mensagem) {
        message.setProperty("p_payloadValido", "false")
        message.setProperty("p_mensagemValidacao", escapar(mensagem))
    } else {
        message.setProperty("p_payloadValido", "true")
        message.setProperty("p_mensagemValidacao", "")
    }
    return message
}

String materializar(Message message) {
    String texto = comoTexto(message.getProperties().get("p_bodyOriginal"))
    if (!texto.trim()) {
        try {
            texto = comoTexto(message.getBody(String.class))
        } catch (ignored) {
            texto = ""
        }
    }
    if (!texto.trim()) {
        try {
            texto = comoTexto(message.getBody(java.io.InputStream.class))
        } catch (ignored) {
            texto = ""
        }
    }
    if (texto == null) {
        texto = ""
    }
    message.setProperty("p_bodyOriginal", texto)
    return texto
}

String comoTexto(def valor) {
    if (valor == null) {
        return ""
    }
    if (valor instanceof CharSequence) {
        return valor.toString()
    }
    if (valor instanceof byte[]) {
        return new String((byte[]) valor, "UTF-8")
    }
    if (valor instanceof InputStream) {
        return ((InputStream) valor).getText("UTF-8")
    }
    if (valor instanceof Reader) {
        return ((Reader) valor).getText()
    }
    try {
        def viaCharset = valor.getText("UTF-8")
        if (viaCharset != null) {
            return viaCharset.toString()
        }
    } catch (ignored) {
    }
    try {
        def viaTexto = valor.getText()
        if (viaTexto != null) {
            return viaTexto.toString()
        }
    } catch (ignored) {
    }
    return ""
}

String validar(String json, List<String> cabecalho, String nomeArray, List<String> camposItem) {
    if (!json?.trim()) {
        return "JSON ausente."
    }
    def raiz
    try {
        raiz = new JsonSlurper().parseText(json)
    } catch (ignored) {
        return "JSON invalido."
    }
    if (!(raiz instanceof Map)) {
        return "JSON invalido."
    }
    List<String> faltando = []
    cabecalho.each { campo ->
        if (!preenchido(raiz[campo])) {
            faltando.add(campo)
        }
    }
    if (nomeArray) {
        def itens = raiz[nomeArray]
        boolean itemOk = false
        if (itens instanceof List && camposItem) {
            itemOk = itens.any { item ->
                item instanceof Map && camposItem.every { preenchido(item[it]) }
            }
        }
        if (!itemOk) {
            faltando.add(nomeArray)
        }
    }
    if (!faltando) {
        return ""
    }
    return "Campos obrigatorios ausentes: " + faltando.join(", ")
}

boolean preenchido(def valor) {
    if (valor == null) {
        return false
    }
    if (valor instanceof List || valor instanceof Map) {
        return false
    }
    return valor.toString().trim().length() > 0
}

String escapar(String texto) {
    return texto.replace("\\", "\\\\").replace("\"", "\\\"").replace("\r", " ").replace("\n", " ").replace("\${", "{")
}
