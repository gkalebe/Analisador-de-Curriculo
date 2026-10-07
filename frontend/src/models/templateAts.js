import { aplicarSugestoesCurriculo } from "../api/curriculoApi.js";
import { ApiError } from "../api/client.js";

/**
 * Fluxo "Transformar em Template ATS": pede ao backend para reescrever o currículo com as
 * sugestões da análise mais recente (POST .../edicao/aplicar-sugestoes). A reescrita é
 * determinística, feita só com o que a análise já salvou — não há nova chamada à IA. O
 * resultado fica em `dados_editados`, e a tela de exportação abre com esse currículo na
 * versão "editada".
 *
 * Nunca lança: se não houver sugestões (400) ou nada puder ser aplicado, devolve um aviso e
 * segue para a galeria com a versão original, para o usuário não ficar travado.
 */
export async function prepararCurriculoParaTemplate(idCurriculo, email) {
  try {
    const resposta = await aplicarSugestoesCurriculo(idCurriculo, email);
    const relatorio = resposta?.relatorio_aplicacao || null;
    const aplicou = (relatorio?.total_aplicadas ?? 0) > 0 && resposta?.possui_edicao;
    return {
      versao: aplicou ? "editada" : "original",
      aviso: resumirRelatorio(relatorio, aplicou),
      relatorio,
    };
  } catch (e) {
    let aviso;
    if (e instanceof ApiError && e.status === 400) {
      aviso = "Esta análise não trouxe sugestões para aplicar. Seguimos com o currículo original.";
    } else {
      aviso = e instanceof ApiError ? e.message : "Não foi possível aplicar as sugestões. Seguimos com o currículo original.";
    }
    return { versao: "original", aviso, relatorio: null };
  }
}

function resumirRelatorio(relatorio, aplicou) {
  if (!relatorio) return "";
  const partes = [];
  const reescritas = relatorio.reescritas || {};
  const remocoes = relatorio.remocoes || {};

  if (!aplicou) {
    partes.push("Nenhuma sugestão da análise pôde ser aplicada automaticamente ao currículo, então seguimos com o original.");
  } else {
    if (reescritas.total) partes.push(`${reescritas.aplicadas} de ${reescritas.total} reescrita(s) aplicada(s)`);
    if (remocoes.total) partes.push(`${(remocoes.aplicadas || []).length} de ${remocoes.total} remoção(ões) aplicada(s)`);
  }

  const pendentes = [...(reescritas.nao_aplicadas || []), ...(remocoes.nao_aplicadas || [])];
  if (aplicou && pendentes.length) {
    partes.push(`não localizamos no currículo: "${pendentes.slice(0, 2).join('", "')}"${pendentes.length > 2 ? "..." : ""}`);
  }

  const palavras = relatorio.palavras_chave_faltantes || [];
  if (palavras.length) {
    partes.push(`palavras-chave ausentes (${palavras.slice(0, 4).join(", ")}${palavras.length > 4 ? "..." : ""}) não são inseridas automaticamente: adicione só o que você realmente domina`);
  }

  return partes.length ? partes.join(" · ") : "";
}

export function montarRotaGaleriaTemplates(email, idCurriculo, versao, aviso) {
  const params = new URLSearchParams({ email });
  if (idCurriculo) params.set("curriculo", idCurriculo);
  if (versao) params.set("versao", versao);
  if (aviso) params.set("aviso", aviso);
  return `/templates?${params.toString()}`;
}

export function montarRotaExportarTemplate(email, idTemplate, idCurriculo, versao) {
  const params = new URLSearchParams({ email, template: idTemplate });
  if (idCurriculo) params.set("curriculo", idCurriculo);
  if (versao) params.set("versao", versao);
  return `/templates/exportar?${params.toString()}`;
}
