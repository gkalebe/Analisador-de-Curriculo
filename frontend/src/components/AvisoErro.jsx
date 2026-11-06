import { Link } from "react-router-dom";
import { ApiError } from "../api/client.js";

/**
 * Converte qualquer exceção no formato de erro de tela `{mensagem, codigo, renovacaoEm}`.
 * ApiError traz a mensagem do backend (inclusive quando `detail` é objeto, como na cota de IA);
 * qualquer outra falha (rede, bug) usa `mensagemPadrao`.
 */
export function paraErroTela(erro, mensagemPadrao) {
  if (erro instanceof ApiError) {
    return { mensagem: erro.message, codigo: erro.codigo, renovacaoEm: erro.renovacao_em, status: erro.status };
  }
  return { mensagem: mensagemPadrao, codigo: null, renovacaoEm: null, status: null };
}

export function formatarDataRenovacao(iso) {
  if (!iso) return "";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeZone: "America/Sao_Paulo" }).format(data);
}

/**
 * Faixa de erro. Quando a cota de IA do plano acabou (`codigo === "cota_ia_excedida"`),
 * informa a data de renovação e leva o usuário para /planos.
 */
export default function AvisoErro({ erro, className = "rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700" }) {
  if (!erro?.mensagem) return null;
  const cotaExcedida = erro.codigo === "cota_ia_excedida";
  const renovacao = cotaExcedida ? formatarDataRenovacao(erro.renovacaoEm) : "";

  return (
    <div role="alert" className={className}>
      <p>{erro.mensagem}</p>
      {cotaExcedida && (
        <p className="mt-1 text-sm">
          {renovacao ? `Sua cota renova em ${renovacao}. ` : ""}
          <Link to="/planos" className="font-bold underline">
            Ver planos
          </Link>{" "}
          para ter mais uso agora.
        </p>
      )}
    </div>
  );
}
