/**
 * @typedef {Object} CurriculoEnviado
 * @property {string} id_curriculo
 * @property {string} nome_arquivo
 * @property {number} tamanho_texto_extraido
 */

export const EXTENSOES_SUPORTADAS = ["pdf", "docx"];
export const TAMANHO_MAXIMO_BYTES = 5 * 1024 * 1024;

export function validarArquivoCurriculo(file) {
  if (!file) return "Selecione um arquivo.";
  const extensao = file.name.split(".").pop()?.toLowerCase();
  if (!extensao || !EXTENSOES_SUPORTADAS.includes(extensao)) {
    return "Formato não suportado. Use apenas arquivos PDF ou DOCX.";
  }
  if (file.size > TAMANHO_MAXIMO_BYTES) {
    return "O arquivo excede o limite de 5MB.";
  }
  return null;
}

export function formatarTamanhoArquivo(bytes) {
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

export function formatarDataUpload(dataIso) {
  if (!dataIso) return "";
  try {
    const d = new Date(dataIso);
    return d.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dataIso;
  }
}

