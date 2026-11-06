import { lerSessao } from "../models/usuario.js";

const urlOriginal = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const API_URL =
  urlOriginal && !urlOriginal.startsWith("http://") && !urlOriginal.startsWith("https://")
    ? `https://${urlOriginal}`
    : urlOriginal;

const MENSAGEM_PADRAO = "Erro na requisição.";

/**
 * O backend devolve `detail` em três formatos: texto (HTTPException comum), objeto
 * `{codigo, mensagem, ...}` (cota de IA excedida, ciclo de cobrança indisponível) ou lista de
 * erros de validação do FastAPI/Pydantic (422). Devolve a melhor mensagem legível para cada um.
 */
function mensagemDoErro(status, corpo) {
  const detail = corpo?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    if (typeof detail.mensagem === "string" && detail.mensagem.trim()) return detail.mensagem;
  }
  if (Array.isArray(detail)) {
    const mensagens = detail
      .map((item) => (typeof item?.msg === "string" ? item.msg.replace(/^Value error, /, "") : ""))
      .filter(Boolean);
    if (mensagens.length > 0) return mensagens.join(" ");
  }
  if (status === 429) return "Muitas requisições em pouco tempo. Aguarde um instante e tente novamente.";
  if (status >= 500) return "O servidor não conseguiu concluir a operação. Tente novamente em instantes.";
  return MENSAGEM_PADRAO;
}

export class ApiError extends Error {
  constructor(status, body) {
    super(mensagemDoErro(status, body));
    this.status = status;
    this.body = body;
    const detail = body?.detail;
    const detalheObjeto = detail && typeof detail === "object" && !Array.isArray(detail) ? detail : null;
    // Presentes quando `detail` é objeto, p.ex. cota_ia_excedida (com renovacao_em, ISO 8601).
    this.codigo = detalheObjeto?.codigo ?? null;
    this.renovacao_em = detalheObjeto?.renovacao_em ?? null;
  }
}

/**
 * Wrapper único de fetch usado por toda a camada de API — trata JSON de entrada/saída
 * e transforma respostas de erro em ApiError, para os componentes não lidarem com fetch cru.
 */
export async function requisitar(caminho, { method = "GET", body, params, token } = {}) {
  const url = new URL(caminho, API_URL);
  if (params) {
    Object.entries(params).forEach(([chave, valor]) => {
      if (valor !== undefined && valor !== null && valor !== "") {
        url.searchParams.set(chave, valor);
      }
    });
  }

  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  const tokenSessao = token || lerSessao()?.accessToken;
  if (tokenSessao) headers.Authorization = `Bearer ${tokenSessao}`;

  const resposta = await fetch(url, {
    method,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  const corpo = resposta.status === 204 ? null : await resposta.json().catch(() => null);

  if (!resposta.ok) {
    throw new ApiError(resposta.status, corpo);
  }

  return corpo;
}

/**
 * Variante de requisitar() para envio de arquivos (multipart/form-data) — usada só pelo
 * upload de currículo, os demais endpoints trafegam JSON via requisitar().
 */
export async function requisitarComArquivo(caminho, formData) {
  const url = new URL(caminho, API_URL);
  const token = lerSessao()?.accessToken;
  const resposta = await fetch(url, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData,
  });

  const corpo = resposta.status === 204 ? null : await resposta.json().catch(() => null);

  if (!resposta.ok) {
    throw new ApiError(resposta.status, corpo);
  }

  return corpo;
}

/**
 * Variante de requisitar() para respostas binárias (PDF/DOCX) — usada pela exportação de
 * templates. Devolve o blob e o nome de arquivo sugerido pelo servidor (Content-Disposition).
 */
export async function requisitarArquivo(caminho, { params } = {}) {
  const url = new URL(caminho, API_URL);
  if (params) {
    Object.entries(params).forEach(([chave, valor]) => {
      if (valor !== undefined && valor !== null && valor !== "") {
        url.searchParams.set(chave, valor);
      }
    });
  }

  const token = lerSessao()?.accessToken;
  const resposta = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });

  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    throw new ApiError(resposta.status, corpo);
  }

  const blob = await resposta.blob();
  const nomeArquivo = extrairNomeArquivo(resposta.headers.get("Content-Disposition"));
  return { blob, nomeArquivo };
}

function extrairNomeArquivo(cabecalhoDisposition) {
  if (!cabecalhoDisposition) return "";
  const combinado = cabecalhoDisposition.match(/filename\*=UTF-8''([^;]+)/);
  if (combinado) return decodeURIComponent(combinado[1]);
  const simples = cabecalhoDisposition.match(/filename="?([^";]+)"?/);
  return simples ? simples[1] : "";
}
