import { Link, useNavigate } from "react-router-dom";
import { lerSessao, limparSessao } from "../models/usuario.js";

const ITENS = [
  { chave: "analise", rotulo: "Nova análise", icone: "ti-search", rota: "/analises/nova" },
  { chave: "historico", rotulo: "Histórico", icone: "ti-history", rota: "/analises/historico" },
  { chave: "vaga", rotulo: "Cadastrar vaga", icone: "ti-briefcase", rota: "/analises/vagas/nova" },
  { chave: "curriculo", rotulo: "Currículo", icone: "ti-file-text", rota: "/analises/upload" },
  { chave: "editar", rotulo: "Editar currículo", icone: "ti-edit", rota: "/analises/editar" },
  { chave: "templates", rotulo: "Templates ATS", icone: "ti-layout-grid", rota: "/templates" },
  { chave: "chatbot", rotulo: "ChatBOT", icone: "ti-robot", rota: "/analises/chat" },
];

export default function Sidebar({ email, ativo }) {
  const navigate = useNavigate();
  const emailAtivo = email || lerSessao()?.email || "";

  function irPara(rota) {
    navigate(emailAtivo ? `${rota}?email=${encodeURIComponent(emailAtivo)}` : rota);
  }

  function sair() {
    limparSessao();
    navigate("/login");
  }

  return (
    <aside className="bg-[#06331d] text-white w-full md:w-64 shrink-0 flex flex-col gap-6 p-6 md:h-screen md:sticky md:top-0 md:overflow-y-auto z-20">
      <Link to="/" className="border-b border-[#8e8e8e]/40 pb-4 font-brand text-[28px] text-white no-underline">
        currículo<span className="font-normal">IA</span>
      </Link>

      <nav className="flex flex-col gap-1.5 flex-1">
        {ITENS.map((item) =>
          item.chave === ativo ? (
            <span
              key={item.chave}
              className="flex items-center gap-3 rounded-lg border border-white/30 bg-white/10 px-3 py-2.5 shadow-inner font-brand text-base font-medium"
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
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 font-brand text-base text-white/80 hover:text-white hover:bg-white/5 transition-colors"
            >
              <i className={`ti ${item.icone}`}></i> {item.rotulo}
            </a>
          )
        )}
      </nav>

      <div className="mt-auto flex flex-col gap-2 pt-4 border-t border-white/10">
        {emailAtivo && (
          <div className="flex items-center gap-3 rounded-lg px-2 py-1.5">
            <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full bg-[#1e5e3f] font-brand text-base font-bold shadow-xs">
              {emailAtivo[0]?.toUpperCase()}
            </span>
            <div className="leading-tight overflow-hidden">
              <p className="font-brand font-semibold text-sm truncate">{emailAtivo.split("@")[0]}</p>
              <p className="text-xs text-white/70 truncate">{emailAtivo}</p>
            </div>
          </div>
        )}
        <button
          onClick={sair}
          className="flex items-center gap-3 rounded-lg px-3 py-2 font-brand text-sm text-white/80 hover:text-white hover:bg-white/5 text-left transition-colors"
        >
          <i className="ti ti-logout"></i> Sair
        </button>
      </div>
    </aside>
  );
}
