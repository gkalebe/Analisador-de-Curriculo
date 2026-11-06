/**
 * Regras da simulação de entrevista sem rede e sem React: validação das respostas e rascunho
 * local (localStorage). O rascunho é só uma conveniência para não perder o texto num F5 — o
 * navegador pode bloquear/limpar o storage, então toda leitura/escrita é protegida e a tela
 * funciona normalmente sem ele.
 */

// Devem acompanhar o schema do backend (app/web/schemas_simulador.py).
export const TAMANHO_MINIMO_RESPOSTA = 10;
export const TAMANHO_MAXIMO_RESPOSTA = 4000;

const PREFIXO_RASCUNHO = "simulacao_rascunho_v1:";

export function respostaValida(texto) {
  const tamanho = (texto || "").trim().length;
  return tamanho >= TAMANHO_MINIMO_RESPOSTA && tamanho <= TAMANHO_MAXIMO_RESPOSTA;
}

export function todasRespondidas(perguntas, rascunho) {
  return perguntas.length > 0 && perguntas.every((p) => respostaValida(rascunho[p.id_pergunta]));
}

export function temRascunho(rascunho) {
  return Object.values(rascunho || {}).some((texto) => (texto || "").trim());
}

export function lerRascunho(idSimulacao) {
  try {
    const bruto = localStorage.getItem(PREFIXO_RASCUNHO + idSimulacao);
    const dados = bruto ? JSON.parse(bruto) : null;
    return dados && typeof dados === "object" && !Array.isArray(dados) ? dados : {};
  } catch {
    return {};
  }
}

export function salvarRascunho(idSimulacao, rascunho) {
  try {
    if (temRascunho(rascunho)) {
      localStorage.setItem(PREFIXO_RASCUNHO + idSimulacao, JSON.stringify(rascunho));
    } else {
      localStorage.removeItem(PREFIXO_RASCUNHO + idSimulacao);
    }
  } catch {
    // Storage indisponível: segue sem rascunho.
  }
}

export function limparRascunho(idSimulacao) {
  try {
    localStorage.removeItem(PREFIXO_RASCUNHO + idSimulacao);
  } catch {
    // Storage indisponível: nada a limpar.
  }
}

/** Linha do histórico (mesmo formato de GET /simulador) a partir de uma simulação completa. */
export function resumirSimulacao(simulacao) {
  const perguntas = simulacao.perguntas || [];
  return {
    id_simulacao: simulacao.id_simulacao,
    id_vaga: simulacao.id_vaga,
    vaga_titulo: simulacao.vaga_titulo,
    data_criacao: simulacao.data_criacao,
    status: simulacao.status,
    legada: simulacao.legada,
    avaliada_em: simulacao.avaliada_em,
    nota_final: simulacao.nota_final,
    total_perguntas: perguntas.length,
    total_respondidas: perguntas.filter((p) => p.resposta).length,
  };
}

export function formatarNota(nota) {
  return nota == null ? "—" : Number(nota).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export function formatarDataHora(iso) {
  if (!iso) return "";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(data);
}
