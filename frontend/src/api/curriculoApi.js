import { requisitar, requisitarComArquivo, API_URL } from "./client.js";

export function enviarCurriculo(email, file) {
  const formData = new FormData();
  formData.append("email", email);
  formData.append("file", file);
  return requisitarComArquivo("/analises/upload", formData);
}

export function listarCurriculos(email) {
  return requisitar("/analises/curriculos", { params: { email } });
}

export function obterDetalhesCurriculo(idCurriculo, email) {
  return requisitar(`/analises/curriculos/${idCurriculo}`, { params: { email } });
}

export function obterUrlDownloadCurriculo(idCurriculo, email) {
  const url = new URL(`/analises/curriculos/${idCurriculo}/download`, API_URL);
  url.searchParams.set("email", email);
  return url.toString();
}

