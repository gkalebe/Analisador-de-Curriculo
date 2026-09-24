import { requisitar, requisitarArquivo, requisitarComArquivo, API_URL } from "./client.js";

export function enviarCurriculo(email, file) {
  const formData = new FormData();
  formData.append("email", email);
  formData.append("file", file);
  return requisitarComArquivo("/analises/upload", formData);
}

export function listarCurriculos(email) {
  return requisitar("/analises/curriculos", { params: { email } });
}

export function listarBibliotecaCurriculos(email) {
  return requisitar("/analises/curriculos/biblioteca", { params: { email } });
}

export function excluirCurriculo(idCurriculo, email) {
  return requisitar(`/analises/curriculos/${idCurriculo}`, { method: "DELETE", params: { email } });
}

export function obterDetalhesCurriculo(idCurriculo, email) {
  return requisitar(`/analises/curriculos/${idCurriculo}`, { params: { email } });
}

export function obterUrlDownloadCurriculo(idCurriculo, email) {
  const url = new URL(`/analises/curriculos/${idCurriculo}/download`, API_URL);
  url.searchParams.set("email", email);
  return url.toString();
}

export function baixarArquivoCurriculo(idCurriculo, email) {
  return requisitarArquivo(`/analises/curriculos/${idCurriculo}/download`, { params: { email } });
}

export function obterEdicaoCurriculo(idCurriculo, email) {
  return requisitar(`/analises/curriculos/${idCurriculo}/edicao`, { params: { email } });
}

export function salvarEdicaoEstruturada(idCurriculo, email, dados) {
  return requisitar(`/analises/curriculos/${idCurriculo}/edicao`, {
    method: "PUT",
    params: { email },
    body: dados,
  });
}

export function salvarEdicaoTextoLivre(idCurriculo, email, texto) {
  return requisitar(`/analises/curriculos/${idCurriculo}/edicao/texto-livre`, {
    method: "POST",
    params: { email },
    body: { texto },
  });
}

export function aplicarSugestoesCurriculo(idCurriculo, email) {
  return requisitar(`/analises/curriculos/${idCurriculo}/edicao/aplicar-sugestoes`, {
    method: "POST",
    params: { email },
  });
}

