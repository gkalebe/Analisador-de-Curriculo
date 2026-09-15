import { requisitar, requisitarComArquivo } from "./client.js";

export function criarAnalise(email, idVaga, file) {
  const formData = new FormData();
  formData.append("email", email);
  formData.append("id_vaga", idVaga);
  formData.append("file", file);
  return requisitarComArquivo("/analises", formData);
}

export function listarAnalises(email) {
  return requisitar("/analises", { params: { email } });
}
