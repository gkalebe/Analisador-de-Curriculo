import { requisitar } from "./client.js";

export function listarSimulacoes(email) {
  return requisitar("/simulador");
}

export function iniciarSimulacao(email, idVaga) {
  return requisitar("/simulador/iniciar", {
    method: "POST",
    body: { id_vaga: idVaga },
  });
}

export function obterSimulacao(email, idSimulacao) {
  return requisitar(`/simulador/${idSimulacao}`);
}

export function responderPerguntaSimulacao(email, idSimulacao, idPergunta, resposta) {
  return requisitar(`/simulador/${idSimulacao}/perguntas/${idPergunta}/resposta`, {
    method: "POST",
    body: { resposta },
  });
}
