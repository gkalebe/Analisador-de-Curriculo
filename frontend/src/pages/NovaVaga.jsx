import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import { criarVaga, listarVagas } from "../api/vagasApi.js";
import { novoFormularioVaga, preencherFormularioComVaga } from "../models/vaga.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";
import ImportarVagaButton from "../components/ImportarVagaButton.jsx";
import FeedbackCarregamento from "../components/FeedbackCarregamento.jsx";

const LIMITE_DESCRICAO_PADRAO = 20000;
const CAMPOS_OPCIONAIS = [
  ["empresa", "Empresa", "text", 200],
  ["localizacao", "Localização", "text", 200],
  ["modalidade", "Modalidade", "text", 100],
  ["senioridade", "Senioridade", "text", 100],
  ["tipo_contratacao", "Tipo de contratação", "text", 100],
  ["faixa_salarial", "Faixa salarial", "text", 200],
  ["responsabilidades", "Responsabilidades", "textarea", 10000],
  ["requisitos_obrigatorios", "Requisitos obrigatórios", "textarea", 10000],
  ["requisitos_desejaveis", "Requisitos desejáveis", "textarea", 10000],
  ["competencias", "Competências", "textarea", 5000],
  ["idiomas", "Idiomas", "textarea", 2000],
  ["beneficios", "Benefícios", "textarea", 5000],
  ["url_origem", "URL de origem", "url", 2048],
];

export default function NovaVaga() {
  const [searchParams] = useSearchParams();
  const emailInicial = lerSessao()?.email || searchParams.get("email") || "";

  const [form, setForm] = useState(novoFormularioVaga(emailInicial));
  const [vagasSalvas, setVagasSalvas] = useState([]);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [limiteDescricao] = useState(LIMITE_DESCRICAO_PADRAO);

  useEffect(() => {
    if (!emailInicial) return;
    listarVagas(emailInicial)
      .then((resposta) => setVagasSalvas(resposta.vagas))
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setErro("Não encontramos um usuário cadastrado com esse e-mail.");
        }
      });
  }, [emailInicial]);

  function reutilizarVaga(vaga) {
    setForm((atual) => preencherFormularioComVaga(atual, vaga));
    document.getElementById("form-vaga")?.scrollIntoView({ behavior: "smooth" });
  }

  async function aoSalvarVaga(evento) {
    evento.preventDefault();
    setErro("");
    setSucesso("");
    setEnviando(true);
    try {
      await criarVaga({ ...form, email: emailInicial });
      setSucesso("Vaga salva com sucesso.");
      setForm(novoFormularioVaga(emailInicial));
      const resposta = await listarVagas(emailInicial);
      setVagasSalvas(resposta.vagas);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível salvar a vaga. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoImportarVaga(vaga) {
    setForm((atual) => preencherFormularioComVaga(atual, vaga));
    setSucesso("Dados importados para o formulário. Revise as informações e salve a vaga.");
    setErro("");
    document.getElementById("form-vaga")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="vaga" />

      <main className="flex-1 p-6 space-y-4 md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Cadastrar vaga</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Cadastre a vaga de interesse para reaproveitar depois em uma análise — sem precisar colar tudo de novo.
          </p>
        </div>

        {erro && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">{erro}</div>}
        {sucesso && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-700">{sucesso}</div>
        )}

        <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <i className="ti ti-briefcase text-[28px]"></i>
              <h2 className="font-brand text-[28px] text-black">Vaga de interesse</h2>
            </div>
            <ImportarVagaButton email={emailInicial} onImported={aoImportarVaga} disabled={!emailInicial} />
          </div>

          <form id="form-vaga" onSubmit={aoSalvarVaga} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-[#595859]" htmlFor="titulo">
                Título da vaga:
              </label>
              <input
                type="text"
                id="titulo"
                maxLength={200}
                placeholder="Ex: Desenvolvedor Frontend Sênior"
                value={form.titulo}
                onChange={(e) => setForm({ ...form, titulo: e.target.value })}
                className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm placeholder-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
              />
              <p className="mt-1 text-xs text-gray-400">Opcional.</p>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-[#595859]" htmlFor="descricao">
                Descrição da vaga:
              </label>
              <textarea
                id="descricao"
                rows={6}
                required
                maxLength={limiteDescricao}
                placeholder="Cole aqui a descrição completa: responsabilidades, requisitos obrigatórios, diferenciais, cultura da empresa..."
                value={form.descricao}
                onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm placeholder-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
              />
              <p className="mt-1 text-xs text-gray-400">
                {form.descricao.length}/{limiteDescricao} caracteres
              </p>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-[#595859]" htmlFor="area">
                Área:
              </label>
              <input
                type="text"
                id="area"
                maxLength={100}
                value={form.area}
                onChange={(e) => setForm({ ...form, area: e.target.value })}
                className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm placeholder-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
              />
              <p className="mt-1 text-xs text-gray-400">Opcional.</p>
            </div>

            <details>
              <summary className="cursor-pointer text-sm font-semibold text-[#1e5e3f]">
                Informações opcionais para enriquecer a análise
              </summary>
              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                {CAMPOS_OPCIONAIS.map(([campo, rotulo, tipo, limite]) => (
                  <label key={campo} className={["responsabilidades", "requisitos_obrigatorios", "requisitos_desejaveis", "competencias", "idiomas", "beneficios"].includes(campo) ? "sm:col-span-2" : ""}>
                    <span className="mb-1 block text-sm font-medium text-[#595859]">{rotulo}</span>
                    {tipo === "textarea" ? (
                      <textarea
                        id={`campo-${campo}`}
                        name={campo}
                        rows={3}
                        maxLength={limite}
                        value={form[campo]}
                        onChange={(e) => setForm({ ...form, [campo]: e.target.value })}
                        className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm"
                      />
                    ) : (
                      <input
                        id={`campo-${campo}`}
                        name={campo}
                        type={tipo}
                        maxLength={limite}
                        value={form[campo]}
                        onChange={(e) => setForm({ ...form, [campo]: e.target.value })}
                        className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm"
                      />
                    )}
                  </label>
                ))}
              </div>
            </details>

            <button
              type="submit"
              disabled={enviando || !emailInicial}
              className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
            >
              <i className="ti ti-device-floppy"></i>
              {enviando ? "Salvando vaga..." : "Salvar vaga"}
            </button>
            {enviando && (
              <FeedbackCarregamento
                mensagem="Salvando as informações da vaga..."
                detalhe="Quase pronto."
              />
            )}
          </form>
        </div>

        {vagasSalvas.length > 0 && (
          <div className="space-y-2">
            <h2 className="font-brand text-lg font-semibold">Suas vagas salvas</h2>
            <p className="text-sm text-gray-500">Clique em uma vaga para reaproveitar as informações no formulário acima.</p>
            <ul className="space-y-2">
              {vagasSalvas.map((vaga) => (
                <li key={vaga.id_vaga}>
                  <button
                    type="button"
                    onClick={() => reutilizarVaga(vaga)}
                    className="w-full rounded-lg border-[0.5px] border-black bg-white p-4 text-left hover:border-[#1e5e3f]"
                  >
                    <p className="font-medium">{vaga.titulo || "(Sem título)"}</p>
                    <p className="text-sm text-gray-500">{vaga.area || "Área não informada"}</p>
                    {(vaga.empresa || vaga.localizacao || vaga.modalidade) && (
                      <p className="text-xs text-gray-500">
                        {[vaga.empresa, vaga.localizacao, vaga.modalidade].filter(Boolean).join(" · ")}
                      </p>
                    )}
                    <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                      {vaga.descricao.slice(0, 160)}
                      {vaga.descricao.length > 160 ? "…" : ""}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {vagasSalvas.length === 0 && emailInicial && (
          <p className="text-sm text-gray-500">Você ainda não tem nenhuma vaga salva.</p>
        )}
      </main>
    </div>
  );
}
