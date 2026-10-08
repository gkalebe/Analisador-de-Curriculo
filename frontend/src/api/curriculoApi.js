import { requisitar, requisitarArquivo, requisitarComArquivo } from "./client.js";

export function enviarCurriculo(email, file) {
  const formData = new FormData();
  formData.append("file", file);
  return requisitarComArquivo("/analises/upload", formData);
}

export function listarCurriculos(email) {
  return requisitar("/analises/curriculos");
}

export function criarCurriculoManual(email, dados) {
  return requisitar("/analises/curriculos", {
    method: "POST",
    body: dados,
  });
}

export function listarBibliotecaCurriculos(email) {
  return requisitar("/analises/curriculos/biblioteca");
}

export function obterDetalhesCurriculo(idCurriculo, email) {
  return requisitar(`/analises/curriculos/${idCurriculo}`);
}

export function atualizarCurriculo(idCurriculo, email, dados) {
  return requisitar(`/analises/curriculos/${idCurriculo}`, {
    method: "PUT",
    body: dados,
  });
}

export function excluirCurriculo(idCurriculo, email) {
  return requisitar(`/analises/curriculos/${idCurriculo}`, {
    method: "DELETE",
  });
}

export function baixarArquivoCurriculo(idCurriculo, email) {
  return requisitarArquivo(`/analises/curriculos/${idCurriculo}/download`);
}

export function obterEdicaoCurriculo(idCurriculo, email) {
  return requisitar(`/analises/curriculos/${idCurriculo}/edicao`);
}

export function salvarEdicaoEstruturada(idCurriculo, email, dados) {
  return requisitar(`/analises/curriculos/${idCurriculo}/edicao`, {
    method: "PUT",
    body: dados,
  });
}

export function salvarEdicaoTextoLivre(idCurriculo, email, texto) {
  return requisitar(`/analises/curriculos/${idCurriculo}/edicao/texto-livre`, {
    method: "POST",
    body: { texto },
  });
}

export function aplicarSugestoesCurriculo(idCurriculo, email) {
  return requisitar(`/analises/curriculos/${idCurriculo}/edicao/aplicar-sugestoes`, {
    method: "POST",
  });
}
