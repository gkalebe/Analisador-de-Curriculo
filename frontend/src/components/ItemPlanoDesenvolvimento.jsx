export const ESTILO_PRIORIDADE = {
  alta: { rotulo: "Prioridade alta", estilo: "border-rose-200 bg-rose-50 text-rose-900", barra: "bg-rose-500" },
  media: { rotulo: "Prioridade média", estilo: "border-amber-200 bg-amber-50 text-amber-900", barra: "bg-amber-500" },
  baixa: { rotulo: "Prioridade baixa", estilo: "border-sky-200 bg-sky-50 text-sky-900", barra: "bg-sky-500" },
};

export function ListaCertificacoes({ certificacoes, titulo = "Certificações sugeridas" }) {
  if (!certificacoes?.length) return null;
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-wider text-gray-500">{titulo}</p>
      <ul className="mt-1 space-y-1">
        {certificacoes.map((cert) => (
          <li key={cert.nome} className="flex items-start gap-2 text-sm text-gray-800">
            <i className="ti ti-certificate mt-0.5 text-[#1e5e3f]"></i>
            <span>
              <span className="font-semibold">{cert.nome}</span>
              {cert.emissor && <span className="text-gray-500"> · {cert.emissor}</span>}
              {cert.motivo && <span className="block text-xs text-gray-500">{cert.motivo}</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** US-015: um requisito não atendido com sua trilha de estudo e certificações. */
export default function ItemPlanoDesenvolvimento({ item, rodape = null }) {
  const prioridade = ESTILO_PRIORIDADE[item.prioridade] || ESTILO_PRIORIDADE.media;
  return (
    <li
      className="relative flex flex-col gap-3 overflow-hidden rounded-lg border border-gray-200 bg-white p-4 pl-5"
      data-testid="item-plano"
    >
      <span className={`absolute inset-y-0 left-0 w-1.5 ${prioridade.barra}`} aria-hidden="true"></span>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-brand text-base font-bold text-black">{item.competencia}</span>
        <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${prioridade.estilo}`}>
          {prioridade.rotulo}
        </span>
        <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-700">
          {item.tipo === "obrigatorio" ? "Obrigatório" : "Desejável"}
        </span>
      </div>

      <div>
        <p className="text-xs font-bold uppercase tracking-wider text-gray-500">Trilha sugerida</p>
        <ol className="mt-1 space-y-1.5">
          {item.trilha.map((passo, idx) => (
            <li key={idx} className="flex gap-2 text-sm text-gray-700">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#1e5e3f] text-[11px] font-bold text-white">
                {idx + 1}
              </span>
              <span>{passo}</span>
            </li>
          ))}
        </ol>
      </div>

      <ListaCertificacoes certificacoes={item.certificacoes} />
      {rodape}
    </li>
  );
}
