import com.sap.gateway.ip.core.customdev.util.Message

/*
 * Grava qualquer exceção na property responseErro.
 * Motivo do Groovy: não há processor nativo que leia CamelExceptionCaught e grave o texto numa property.
 * Entrada : property CamelExceptionCaught
 * Saída   : property responseErro
 */
Message processData(Message message) {
    def caught = message.getProperties().get("CamelExceptionCaught")
    String texto = "Erro inesperado"
    if (caught != null) {
        def detalhe = caught.getMessage()
        if (detalhe != null && detalhe.toString().trim()) {
            texto = detalhe.toString().trim()
        }
    }
    texto = texto.replace("\\", "\\\\").replace("\"", "\\\"").replace("\r", " ").replace("\n", " ").replace("\${", "{")
    message.setProperty("responseErro", texto)
    return message
}
