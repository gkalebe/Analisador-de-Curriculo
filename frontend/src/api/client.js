export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, body) {
    super(typeof body?.detail === "string" ? body.detail : "Erro na requisição.");
    this.status = status;
    this.body = body;
  }
}

/**
 * Wrapper único de fetch usado por toda a camada de API — trata JSON de entrada/saída
 * e transforma respostas de erro em ApiError, para os componentes não lidarem com fetch cru.
 */
export async function requisitar(caminho, { method = "GET", body, params } = {}) {
  const url = new URL(caminho, API_URL);
  if (params) {
    Object.entries(params).forEach(([chave, valor]) => {
      if (valor !== undefined && valor !== null && valor !== "") {
        url.searchParams.set(chave, valor);
      }
    });
  }

  const resposta = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
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
  const resposta = await fetch(url, { method: "POST", body: formData });

  const corpo = resposta.status === 204 ? null : await resposta.json().catch(() => null);

  if (!resposta.ok) {
    throw new ApiError(resposta.status, corpo);
  }

  return corpo;
}
