import { requisitar } from "./client.js";

export function listarMensagensChat(contextoOuIdCurriculo, emailOpcional) {
  if (typeof contextoOuIdCurriculo === "object" && contextoOuIdCurriculo !== null) {
    const { idCurriculo, idVaga } = contextoOuIdCurriculo;
    const params = {};
    if (idCurriculo) params.id_curriculo = idCurriculo;
    if (idVaga) params.id_vaga = idVaga;
    return requisitar("/chat/mensagens", { params });
  }

  return requisitar(`/chat/curriculos/${contextoOuIdCurriculo}/mensagens`, {
  });
}

export function enviarMensagemChat(contextoOuIdCurriculo, emailOpcional, perguntaOpcional) {
  if (typeof contextoOuIdCurriculo === "object" && contextoOuIdCurriculo !== null) {
    const { pergunta, idCurriculo, idVaga } = contextoOuIdCurriculo;
    return requisitar("/chat/mensagens", {
      method: "POST",
      body: {
        pergunta,
        id_curriculo: idCurriculo || null,
        id_vaga: idVaga || null,
      },
    });
  }

  return requisitar(`/chat/curriculos/${contextoOuIdCurriculo}/mensagens`, {
    method: "POST",
    body: { pergunta: perguntaOpcional },
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
      id_curriculo: idCurriculo || null,
      id_vaga: idVaga || null,
    },
  });
}
