import { requisitar } from "./client.js";

export function listarMensagensChat(idCurriculo, email) {
  return requisitar(`/chat/curriculos/${idCurriculo}/mensagens`, { params: { email } });
}

export function enviarMensagemChat(idCurriculo, email, pergunta) {
  return requisitar(`/chat/curriculos/${idCurriculo}/mensagens`, {
    method: "POST",
    body: { email, pergunta },
  });
}
