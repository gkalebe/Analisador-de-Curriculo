/**
 * Formas de dados relacionadas a vagas — sem nenhuma lógica de rede aqui.
 * As funções que chamam a API ficam em src/api/vagasApi.js.
 */

/**
 * @typedef {Object} Vaga
 * @property {string} id_vaga
 * @property {string|null} titulo
 * @property {string} descricao
 * @property {string|null} requisitos
 * @property {string|null} area
 * @property {string} data_criacao
 */

/** Formulário vazio para o formulário de cadastro de vaga. */
export function novoFormularioVaga(email = "") {
  return { email, titulo: "", descricao: "", requisitos: "", area: "" };
}

/** Preenche o formulário a partir de uma vaga já salva (para reaproveitar). */
export function preencherFormularioComVaga(formulario, vaga) {
  return {
    ...formulario,
    titulo: vaga.titulo || "",
    descricao: vaga.descricao || "",
    requisitos: vaga.requisitos || "",
    area: vaga.area || "",
  };
}
