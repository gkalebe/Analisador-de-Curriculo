import { requisitar, requisitarArquivo } from "./client.js";

export function listarTemplates(email) {
  return requisitar("/templates");
}

export function exportarCurriculo(email, idCurriculo, idTemplate, formato, versao = "original") {
  return requisitarArquivo("/templates/exportar", {
    params: { id_curriculo: idCurriculo, id_template: idTemplate, formato, versao },
  });
}
