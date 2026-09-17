import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import { listarTemplates } from "../api/templateApi.js";
import { ApiError } from "../api/client.js";

const ESTILOS_CARTAO = {
  moderno: {
    borda: "border-[#1e5e3f]",
    nome: "text-[#1e5e3f] font-brand text-xl font-bold",
    secao: "text-[#1e5e3f] text-xs font-bold uppercase tracking-wide mt-3",
    corpo: "text-sm text-gray-700",
  },
  classico: {
    borda: "border-black",
    nome: "text-black font-serif text-xl font-bold text-center block",
    secao: "text-black text-xs font-bold uppercase text-center block mt-3",
    corpo: "text-sm text-gray-800 text-center",
  },
  minimalista: {
    borda: "border-gray-300",
    nome: "text-gray-900 text-lg font-normal",
    secao: "text-gray-400 text-xs font-medium uppercase mt-3",
    corpo: "text-sm text-gray-600",
  },
};

export default function GaleriaTemplates() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const emailInicial = searchParams.get("email") || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [templates, setTemplates] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [avisoBloqueio, setAvisoBloqueio] = useState("");

  useEffect(() => {
    if (!emailInicial) return;
    setCarregando(true);
    setErro("");
    setAvisoBloqueio("");
    listarTemplates(emailInicial)
      .then((resposta) => setTemplates(resposta.templates))
      .catch((e) => {
        if (e instanceof ApiError && e.status === 403) {
          setAvisoBloqueio(e.message);
        } else if (e instanceof ApiError && e.status === 404) {
          setErro("Não encontramos um usuário cadastrado com esse e-mail.");
        } else {
          setErro("Não foi possível carregar os templates. Tente novamente.");
        }
      })
      .finally(() => setCarregando(false));
  }, [emailInicial]);

  function entrarComEmail(evento) {
    evento.preventDefault();
    setSearchParams({ email: emailCampo });
  }

  function usarTemplate(idTemplate) {
    navigate(`/templates/exportar?email=${encodeURIComponent(emailInicial)}&template=${idTemplate}`);
  }

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="templates" />

      <main className="flex-1 p-6 space-y-4 md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Templates ATS</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Escolha um modelo profissional para o seu currículo.
          </p>
        </div>

        {!emailInicial && (
          <form onSubmit={entrarComEmail} className="flex gap-2 rounded-lg border-[0.5px] border-black bg-white p-4">
            <input
              type="email"
              value={emailCampo}
              onChange={(e) => setEmailCampo(e.target.value)}
              placeholder="Seu e-mail cadastrado"
              required
              className="flex-1 rounded border border-[#dfdfe0] px-3 py-2 text-sm text-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
            />
            <button type="submit" className="rounded bg-[#1e5e3f] px-4 py-2 font-bold text-white hover:bg-[#174a32]">
              Entrar
            </button>
          </form>
        )}

        {carregando && <p className="text-sm text-gray-500">Carregando templates...</p>}

        {erro && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">{erro}</div>}

        {avisoBloqueio && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800">
            {avisoBloqueio}
          </div>
        )}

        {templates.length > 0 && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {templates.map((template) => {
              const estilo = ESTILOS_CARTAO[template.id_template] || ESTILOS_CARTAO.moderno;
              const preview = template.preview_ficticio;
              return (
                <div
                  key={template.id_template}
                  className={`flex flex-col rounded-lg border-[1.5px] ${estilo.borda} bg-white p-5 shadow-sm`}
                >
                  <div className="mb-4">
                    <p className={estilo.nome}>{preview.nome}</p>
                    <p className="text-xs text-gray-500">
                      {preview.email} · {preview.telefone}
                    </p>
                    <p className={estilo.secao}>Resumo</p>
                    <p className={estilo.corpo}>{preview.resumo}</p>
                    <p className={estilo.secao}>Experiência</p>
                    <p className={`${estilo.corpo} whitespace-pre-line`}>{preview.experiencia_profissional}</p>
                    <p className={estilo.secao}>Habilidades</p>
                    <p className={estilo.corpo}>{preview.habilidades}</p>
                  </div>
                  <div className="mt-auto space-y-2 border-t border-gray-100 pt-4">
                    <p className="font-brand text-lg font-semibold text-black">{template.nome}</p>
                    <p className="text-sm text-gray-500">{template.descricao}</p>
                    <button
                      onClick={() => usarTemplate(template.id_template)}
                      className="w-full rounded-md bg-[#1e5e3f] px-4 py-2 font-bold text-white hover:bg-[#174a32]"
                    >
                      Usar este template
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
