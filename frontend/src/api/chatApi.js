import { requisitar } from "./client.js";

export function listarMensagensChat(contextoOuIdCurriculo, emailOpcional) {
  if (typeof contextoOuIdCurriculo === "object" && contextoOuIdCurriculo !== null) {
    const { email, idCurriculo, idVaga } = contextoOuIdCurriculo;
    const params = { email };
    if (idCurriculo) params.id_curriculo = idCurriculo;
    if (idVaga) params.id_vaga = idVaga;
    return requisitar("/chat/mensagens", { params });
  }

  return requisitar(`/chat/curriculos/${contextoOuIdCurriculo}/mensagens`, {
    params: { email: emailOpcional },
  });
}

export function enviarMensagemChat(contextoOuIdCurriculo, emailOpcional, perguntaOpcional) {
  if (typeof contextoOuIdCurriculo === "object" && contextoOuIdCurriculo !== null) {
    const { email, pergunta, idCurriculo, idVaga } = contextoOuIdCurriculo;
    return requisitar("/chat/mensagens", {
      method: "POST",
      body: {
        email,
        pergunta,
        id_curriculo: idCurriculo || null,
        id_vaga: idVaga || null,
      },
    });
  }

  return requisitar(`/chat/curriculos/${contextoOuIdCurriculo}/mensagens`, {
    method: "POST",
    body: { email: emailOpcional, pergunta: perguntaOpcional },
  });
}

/**
 * Encerra a conversa (chamado ao sair do ChatBOT): apaga as mensagens do banco, preservando
 * antes apenas as perguntas anonimizadas na árvore de dados do sistema.
 */
export function encerrarConversaChat({ email, idCurriculo, idVaga }) {
  return requisitar("/chat/encerrar", {
    method: "POST",
    body: {
      email,
      id_curriculo: idCurriculo || null,
      id_vaga: idVaga || null,
    },
  });
}
