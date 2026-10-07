import { requisitar, requisitarComArquivo } from "./client.js";

export function criarAnalise(emailOuPayload, idVaga, file) {
  const formData = new FormData();
  if (typeof emailOuPayload === "object" && emailOuPayload !== null) {
    formData.append("email", emailOuPayload.email);
    formData.append("id_vaga", emailOuPayload.idVaga);
    if (emailOuPayload.idCurriculo) {
      formData.append("id_curriculo", emailOuPayload.idCurriculo);
    }
    if (emailOuPayload.file) {
      formData.append("file", emailOuPayload.file);
    }
  } else {
    formData.append("email", emailOuPayload);
    formData.append("id_vaga", idVaga);
    if (typeof file === "string") {
      formData.append("id_curriculo", file);
    } else if (file) {
      formData.append("file", file);
    }
  }
  return requisitarComArquivo("/analises", formData);
}

export function listarAnalises(email) {
  return requisitar("/analises", { params: { email } });
}

export function excluirAnalise(idAnalise, email) {
  return requisitar(`/analises/${idAnalise}`, { method: "DELETE", params: { email } });
}
