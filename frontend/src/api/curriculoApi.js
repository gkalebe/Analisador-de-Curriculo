import { requisitarComArquivo } from "./client.js";

export function enviarCurriculo(email, file) {
  const formData = new FormData();
  formData.append("email", email);
  formData.append("file", file);
  return requisitarComArquivo("/analises/upload", formData);
}
