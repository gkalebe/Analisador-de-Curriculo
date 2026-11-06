import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ItemPlanoDesenvolvimento, { ListaCertificacoes } from "./ItemPlanoDesenvolvimento.jsx";
import { obterPlanoDesenvolvimentoAnalise } from "../api/analiseApi.js";
import { ApiError } from "../api/client.js";

/** US-015: trilha/certificação para cada requisito não atendido de uma análise. */
export default function PlanoDesenvolvimentoAnalise({ idAnalise, email }) {
  const [plano, setPlano] = useState(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!idAnalise) return;
    let ativo = true;
    obterPlanoDesenvolvimentoAnalise(idAnalise)
      .then((resposta) => ativo && setPlano(resposta))
      .catch((e) => ativo && setErro(e instanceof ApiError ? e.message : "Não foi possível carregar o plano."));
    return () => {
      ativo = false;
    };
  }, [idAnalise]);

  return (
    <section
      aria-labelledby="plano-analise-titulo"
      className="rounded-xl border-[0.5px] border-black bg-white p-6 space-y-4"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-2">
          <i className="ti ti-route text-[22px] text-[#1e5e3f]"></i>
          <div>
            <h3 id="plano-analise-titulo" className="font-brand text-lg font-bold text-black">
              Plano de desenvolvimento
            </h3>
            <p className="text-sm text-gray-600">Trilhas e certificações para os requisitos que faltam nesta vaga.</p>
          </div>
        </div>
        <Link
          to={`/plano-desenvolvimento?email=${encodeURIComponent(email || "")}`}
          className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-[#1e5e3f] hover:underline"
        >
          Ver plano completo <i className="ti ti-arrow-right"></i>
        </Link>
      </div>

      {erro && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {erro}
        </p>
      )}
      {!plano && !erro && <p className="text-sm text-gray-500">Carregando plano...</p>}

      {plano?.sem_lacunas && (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {plano.mensagem}
        </p>
      )}
      {plano?.itens?.length > 0 && (
        <ul className="grid gap-3 md:grid-cols-2">
          {plano.itens.map((item) => (
            <ItemPlanoDesenvolvimento key={item.competencia} item={item} />
          ))}
        </ul>
      )}
      {plano?.certificacoes_opcionais?.length > 0 && (
        <ListaCertificacoes certificacoes={plano.certificacoes_opcionais} titulo="Certificações opcionais" />
      )}
    </section>
  );
}
