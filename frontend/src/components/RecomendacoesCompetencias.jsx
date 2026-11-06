import { useEffect, useState } from "react";
import { obterRecomendacoesCompetencias } from "../api/analiseApi.js";
import { ApiError } from "../api/client.js";

const ROTULO_STATUS = {
  parcial: { texto: "Pouco destacada", estilo: "border-amber-200 bg-amber-50 text-amber-900" },
  nao_evidenciado: { texto: "Não encontrada", estilo: "border-rose-200 bg-rose-50 text-rose-900" },
};

const ROTULO_ONDE = {
  resumo: "Resumo profissional",
  experiencia_profissional: "Experiência profissional",
  habilidades: "Habilidades",
  formacao: "Formação",
  projetos: "Projetos",
};

/**
 * US-014: uma recomendação por competência em lacuna, vinda de GET /analises/{id}/recomendacoes.
 * O backend garante ao menos uma orientação por lacuna e nunca sugere dados inexistentes.
 */
export default function RecomendacoesCompetencias({ idAnalise }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    if (!idAnalise) return;
    let ativo = true;
    setCarregando(true);
    setErro("");
    obterRecomendacoesCompetencias(idAnalise)
      .then((resposta) => ativo && setDados(resposta))
      .catch((e) => {
        if (!ativo) return;
        setErro(e instanceof ApiError ? e.message : "Não foi possível carregar as recomendações.");
      })
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, [idAnalise]);

  return (
    <section
      aria-labelledby="recomendacoes-competencias-titulo"
      className="rounded-xl border-[0.5px] border-black bg-white p-6 space-y-4"
    >
      <div className="flex items-start gap-2">
        <i className="ti ti-bulb text-[22px] text-[#1e5e3f]"></i>
        <div>
          <h3 id="recomendacoes-competencias-titulo" className="font-brand text-lg font-bold text-black">
            Como evidenciar suas competências
          </h3>
          <p className="text-sm text-gray-600">
            Orientações para cada competência que a vaga pede e que está ausente ou pouco destacada no seu
            currículo.
          </p>
        </div>
      </div>

      {carregando && <p className="text-sm text-gray-500">Carregando recomendações...</p>}
      {erro && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {erro}
        </p>
      )}

      {dados?.sem_lacunas && (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Nenhuma competência em lacuna: os requisitos identificados já aparecem no seu currículo.
        </p>
      )}

      {dados?.recomendacoes?.length > 0 && (
        <>
          <p className="flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-900">
            <i className="ti ti-shield-check mt-0.5"></i>
            Inclua no currículo apenas o que você realmente fez. Se não tiver a competência, veja o plano de
            desenvolvimento para adquiri-la.
          </p>
          <ul className="grid gap-3 md:grid-cols-2">
            {dados.recomendacoes.map((rec) => {
              const status = ROTULO_STATUS[rec.status] || ROTULO_STATUS.nao_evidenciado;
              return (
                <li
                  key={rec.competencia}
                  className="flex flex-col gap-2 rounded-lg border border-gray-200 bg-gray-50 p-4"
                  data-testid="recomendacao-competencia"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-black">{rec.competencia}</span>
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${status.estilo}`}>
                      {status.texto}
                    </span>
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs text-gray-700">
                      {rec.tipo === "obrigatorio" ? "Obrigatório" : "Desejável"}
                    </span>
                  </div>
                  <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">
                    {rec.orientacoes.map((orientacao, idx) => (
                      <li key={idx}>{orientacao}</li>
                    ))}
                  </ul>
                  {rec.onde_evidenciar && ROTULO_ONDE[rec.onde_evidenciar] && (
                    <p className="text-xs font-medium text-[#1e5e3f]">
                      <i className="ti ti-map-pin"></i> Onde evidenciar: {ROTULO_ONDE[rec.onde_evidenciar]}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
