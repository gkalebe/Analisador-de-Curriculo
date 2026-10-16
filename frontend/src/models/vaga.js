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
 * @property {string|null} empresa
 * @property {string|null} localizacao
 * @property {string|null} modalidade
 * @property {string|null} senioridade
 * @property {string|null} tipo_contratacao
 * @property {string|null} faixa_salarial
 * @property {string|null} responsabilidades
 * @property {string|null} requisitos_obrigatorios
 * @property {string|null} requisitos_desejaveis
 * @property {string|null} competencias
 * @property {string|null} idiomas
 * @property {string|null} beneficios
 * @property {string|null} url_origem
 * @property {string} data_criacao
 */

/** Formulário vazio para o formulário de cadastro de vaga. */
export function novoFormularioVaga(email = "") {
  return {
    email,
    titulo: "",
    descricao: "",
    requisitos: "",
    area: "",
    empresa: "",
    localizacao: "",
    modalidade: "",
    senioridade: "",
    tipo_contratacao: "",
    faixa_salarial: "",
    responsabilidades: "",
    requisitos_obrigatorios: "",
    requisitos_desejaveis: "",
    competencias: "",
    idiomas: "",
    beneficios: "",
    url_origem: "",
  };
}

/** Preenche o formulário a partir de uma vaga já salva (para reaproveitar). */
export function preencherFormularioComVaga(formulario, vaga) {
  return {
    ...formulario,
    titulo: vaga.titulo || "",
    descricao: vaga.descricao || "",
    requisitos: vaga.requisitos || "",
    area: vaga.area || "",
    empresa: vaga.empresa || "",
    localizacao: vaga.localizacao || "",
    modalidade: vaga.modalidade || "",
    senioridade: vaga.senioridade || "",
    tipo_contratacao: vaga.tipo_contratacao || "",
    faixa_salarial: vaga.faixa_salarial || "",
    responsabilidades: vaga.responsabilidades || "",
    requisitos_obrigatorios: vaga.requisitos_obrigatorios || "",
    requisitos_desejaveis: vaga.requisitos_desejaveis || "",
    competencias: vaga.competencias || "",
    idiomas: vaga.idiomas || "",
    beneficios: vaga.beneficios || "",
    url_origem: vaga.url_origem || "",
  };
}
