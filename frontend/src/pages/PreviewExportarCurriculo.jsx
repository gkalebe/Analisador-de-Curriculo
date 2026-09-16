import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import { exportarCurriculo, listarTemplates } from "../api/templateApi.js";
import { listarAnalises } from "../api/analiseApi.js";
import { ApiError } from "../api/client.js";

export default function PreviewExportarCurriculo() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || "";
  const idTemplate = searchParams.get("template") || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [templates, setTemplates] = useState([]);
  const [analises, setAnalises] = useState([]);
  const [idCurriculoSelecionado, setIdCurriculoSelecionado] = useState("");
  const [urlPreview, setUrlPreview] = useState("");
  const [carregandoPreview, setCarregandoPreview] = useState(false);
  const [exportando, setExportando] = useState("");
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!emailInicial) return;
    listarTemplates(emailInicial)
      .then((resposta) => setTemplates(resposta.templates))
      .catch(() => {});
    listarAnalises(emailInicial)
      .then((resposta) => setAnalises(resposta.analises))
      .catch(() => {});
  }, [emailInicial]);

  useEffect(() => {
    return () => {
      if (urlPreview) URL.revokeObjectURL(urlPreview);
    };
  }, [urlPreview]);

  function entrarComEmail(evento) {
    evento.preventDefault();
    setSearchParams({ email: emailCampo, template: idTemplate });
  }

  const templateEscolhido = templates.find((t) => t.id_template === idTemplate);

  async function prever() {
    if (!idCurriculoSelecionado) return;
    setErro("");
    setCarregandoPreview(true);
    try {
      const { blob } = await exportarCurriculo(emailInicial, idCurriculoSelecionado, idTemplate, "pdf");
      if (urlPreview) URL.revokeObjectURL(urlPreview);
      setUrlPreview(URL.createObjectURL(blob));
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível gerar a pré-visualização.");
    } finally {
      setCarregandoPreview(false);
    }
  }

  async function exportar(formato) {
    if (!idCurriculoSelecionado) return;
    setErro("");
    setExportando(formato);
    try {
      const { blob, nomeArquivo } = await exportarCurriculo(emailInicial, idCurriculoSelecionado, idTemplate, formato);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = nomeArquivo || `curriculo.${formato}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível exportar o currículo.");
    } finally {
      setExportando("");
    }
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900">
      <Sidebar email={emailInicial} ativo="templates" />

      <main className="flex-1 p-6 space-y-4">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Preview e exportação</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            {templateEscolhido
              ? `Template: ${templateEscolhido.nome}`
              : "Escolha um currículo e exporte no template selecionado."}
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

        {emailInicial && !idTemplate && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800">
            Selecione um template antes.{" "}
            <Link
              className="font-semibold underline"
              to={`/templates?email=${encodeURIComponent(emailInicial)}`}
            >
              Ver templates
            </Link>
          </div>
        )}

        {erro && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">{erro}</div>}

        {emailInicial && idTemplate && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-6">
            <div className="flex items-center gap-3">
              <i className="ti ti-file-text text-[28px]"></i>
              <h2 className="font-brand text-[28px] text-black">Escolha o currículo</h2>
            </div>

            {analises.length === 0 && (
              <p className="text-sm text-gray-500">
                Você ainda não concluiu nenhuma análise. Rode uma em "Nova análise" antes de exportar um template.
              </p>
            )}

            {analises.length > 0 && (
              <ul className="space-y-2">
                {analises.map((analise) => (
                  <li key={analise.id_analise}>
                    <label
                      className={`flex cursor-pointer items-start gap-3 rounded-lg border-[0.5px] p-4 hover:border-[#1e5e3f] ${
                        idCurriculoSelecionado === analise.id_curriculo
                          ? "border-[#1e5e3f] bg-[#f0fdf4]"
                          : "border-black"
                      }`}
                    >
                      <input
                        type="radio"
                        name="curriculo"
                        value={analise.id_curriculo}
                        checked={idCurriculoSelecionado === analise.id_curriculo}
                        onChange={(e) => {
                          setIdCurriculoSelecionado(e.target.value);
                          if (urlPreview) URL.revokeObjectURL(urlPreview);
                          setUrlPreview("");
                        }}
                        className="mt-1"
                      />
                      <div>
                        <p className="font-medium">
                          Análise de {new Date(analise.data_analise).toLocaleDateString("pt-BR")}
                        </p>
                        {analise.pontuacao != null && (
                          <p className="text-sm text-gray-500">Pontuação: {analise.pontuacao}</p>
                        )}
                      </div>
                    </label>
                  </li>
                ))}
              </ul>
            )}

            {idCurriculoSelecionado && (
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={prever}
                  disabled={carregandoPreview}
                  className="flex items-center gap-2 rounded-md border border-[#1e5e3f] px-4 py-3 font-bold text-[#1e5e3f] hover:bg-[#f0fdf4] disabled:opacity-60"
                >
                  <i className="ti ti-eye"></i> {carregandoPreview ? "Gerando..." : "Pré-visualizar"}
                </button>
                <button
                  onClick={() => exportar("pdf")}
                  disabled={exportando === "pdf"}
                  className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                >
                  <i className="ti ti-download"></i> {exportando === "pdf" ? "Exportando..." : "Exportar PDF"}
                </button>
                <button
                  onClick={() => exportar("docx")}
                  disabled={exportando === "docx"}
                  className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                >
                  <i className="ti ti-download"></i> {exportando === "docx" ? "Exportando..." : "Exportar DOCX"}
                </button>
              </div>
            )}

            {urlPreview && (
              <iframe
                title="Pré-visualização do currículo"
                src={urlPreview}
                className="h-[600px] w-full rounded-lg border border-gray-200"
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
