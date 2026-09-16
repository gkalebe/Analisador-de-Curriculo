import { requisitar, requisitarArquivo } from "./client.js";

export function listarTemplates(email) {
  return requisitar("/templates", { params: { email } });
}

export function exportarCurriculo(email, idCurriculo, idTemplate, formato) {
  return requisitarArquivo("/templates/exportar", {
    params: { email, id_curriculo: idCurriculo, id_template: idTemplate, formato },
  });
}
