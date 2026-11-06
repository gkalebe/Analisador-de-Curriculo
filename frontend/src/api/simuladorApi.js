import { requisitar } from "./client.js";

export function listarSimulacoes({ limit, offset } = {}) {
  return requisitar("/simulador", { params: { limit, offset } });
}

export function iniciarSimulacao(idVaga) {
  return requisitar("/simulador/iniciar", {
    method: "POST",
    body: { id_vaga: idVaga },
  });
}

export function obterSimulacao(idSimulacao) {
  return requisitar(`/simulador/${idSimulacao}`);
}

/** Nova simulação (novas perguntas) para a mesma vaga; a original não é alterada. */
export function repetirSimulacao(idSimulacao) {
  return requisitar(`/simulador/${idSimulacao}/repetir`, { method: "POST" });
}

/** Exclusão definitiva da entrevista (não devolve a cota já consumida). */
export function excluirSimulacao(idSimulacao) {
  return requisitar(`/simulador/${idSimulacao}`, { method: "DELETE" });
}

/** Avalia todas as respostas de uma vez. `respostas`: { [id_pergunta]: texto }. */
export function avaliarSimulacao(idSimulacao, respostas) {
  return requisitar(`/simulador/${idSimulacao}/avaliar`, {
    method: "POST",
    body: {
      respostas: Object.entries(respostas).map(([idPergunta, resposta]) => ({
        id_pergunta: idPergunta,
        resposta,
      })),
    },
  });
}
