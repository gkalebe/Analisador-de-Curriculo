/**
 * Formas de dados relacionadas a usuário/autenticação — sem nenhuma lógica de rede aqui.
 * As funções que chamam a API ficam em src/api/authApi.js.
 */

/**
 * @typedef {Object} Usuario
 * @property {string} id_usuario
 * @property {string} nome
 * @property {string} email
 */

/**
 * @typedef {Object} LoginResponse
 * @property {string} access_token
 * @property {string} token_type
 * @property {Usuario} usuario
 */

/** Cria o objeto de sessão salvo no localStorage a partir de uma resposta de login. */
export function criarSessao(loginResponse) {
  return {
    accessToken: loginResponse.access_token,
    nome: loginResponse.usuario.nome,
    email: loginResponse.usuario.email,
  };
}

const CHAVES_SESSAO = {
  token: "access_token",
  nome: "usuario_nome",
  email: "usuario_email",
};

export function salvarSessao(sessao) {
  localStorage.setItem(CHAVES_SESSAO.token, sessao.accessToken);
  localStorage.setItem(CHAVES_SESSAO.nome, sessao.nome);
  localStorage.setItem(CHAVES_SESSAO.email, sessao.email);
}

export function lerSessao() {
  const token = localStorage.getItem(CHAVES_SESSAO.token);
  if (!token) return null;
  return {
    accessToken: token,
    nome: localStorage.getItem(CHAVES_SESSAO.nome) || "",
    email: localStorage.getItem(CHAVES_SESSAO.email) || "",
  };
}

export function limparSessao() {
  localStorage.removeItem(CHAVES_SESSAO.token);
  localStorage.removeItem(CHAVES_SESSAO.nome);
  localStorage.removeItem(CHAVES_SESSAO.email);
}
