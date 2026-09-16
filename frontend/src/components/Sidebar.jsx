import { Link, useNavigate } from "react-router-dom";
import { lerSessao } from "../models/usuario.js";

const ITENS = [
  { chave: "analise", rotulo: "Nova análise", icone: "ti-search", rota: "/analises/nova" },
  { chave: "historico", rotulo: "Histórico", icone: "ti-history", rota: "/analises/historico" },
  { chave: "vaga", rotulo: "Cadastrar vaga", icone: "ti-briefcase", rota: "/analises/vagas/nova" },
  { chave: "curriculo", rotulo: "Currículo", icone: "ti-file-text", rota: "/analises/upload" },
  { chave: "templates", rotulo: "Templates ATS", icone: "ti-layout-grid", rota: "/templates" },
];

export default function Sidebar({ email, ativo }) {
  const navigate = useNavigate();
  const emailAtivo = email || lerSessao()?.email || "";

  function irPara(rota) {
    navigate(emailAtivo ? `${rota}?email=${encodeURIComponent(emailAtivo)}` : rota);
  }

  return (
    <aside className="bg-[#06331d] text-white w-full md:w-64 shrink-0 flex flex-col gap-8 p-6">
      <Link to="/" className="border-b border-[#8e8e8e] pb-6 font-brand text-[28px] text-white no-underline">
        currículo<span className="font-normal">IA</span>
      </Link>

      <nav className="flex flex-col gap-3">
        {ITENS.map((item) =>
          item.chave === ativo ? (
            <span
              key={item.chave}
              className="flex items-center gap-3 rounded-lg border border-white/30 bg-white/5 px-3 py-3 shadow-inner font-brand text-lg"
            >
              <i className={`ti ${item.icone}`}></i> {item.rotulo}
            </span>
          ) : (
            <a
              key={item.chave}
              href={item.rota}
              onClick={(e) => {
                e.preventDefault();
                irPara(item.rota);
              }}
              className="flex items-center gap-3 rounded-lg px-3 py-3 font-brand text-lg text-white/90 hover:bg-white/5"
            >
              <i className={`ti ${item.icone}`}></i> {item.rotulo}
            </a>
          )
        )}
        <a href="#" className="flex items-center gap-3 rounded-lg px-3 py-3 font-brand text-lg text-white/90 hover:bg-white/5">
          <i className="ti ti-robot"></i> ChatBOT
        </a>
      </nav>

      <div className="mt-auto flex flex-col gap-3">
        {emailAtivo && (
          <div className="flex items-center gap-3 rounded-lg px-3 py-3">
            <span className="flex h-[44px] w-[44px] items-center justify-center rounded-full bg-[#1e5e3f] font-brand text-lg">
              {emailAtivo[0]?.toUpperCase()}
            </span>
            <div className="leading-tight">
              <p className="font-brand font-semibold">{emailAtivo.split("@")[0]}</p>
              <p className="text-sm text-white/80">{emailAtivo}</p>
            </div>
          </div>
        )}
        <button
          onClick={() => navigate("/painel")}
          className="flex items-center gap-3 rounded-lg px-3 py-3 font-brand text-lg text-white/90 hover:bg-white/5 text-left"
        >
          <i className="ti ti-arrow-left"></i> Voltar ao painel
        </button>
      </div>
    </aside>
  );
}
