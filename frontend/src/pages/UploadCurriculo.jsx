import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import VisualizadorPdf from "../components/VisualizadorPdf.jsx";
import LimiteDeErro from "../components/LimiteDeErro.jsx";
import {
  baixarArquivoCurriculo,
  criarCurriculoManual,
  excluirCurriculo,
  enviarCurriculo,
  obterEdicaoCurriculo,
  listarCurriculos,
  previsualizarCurriculo,
  salvarEdicaoEstruturada,
} from "../api/curriculoApi.js";
import { exportarCurriculo } from "../api/templateApi.js";
import {
  formatarDataUpload,
  formatarTamanhoArquivo,
  validarArquivoCurriculo,
} from "../models/curriculo.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";
import EditorDadosCurriculo from "../components/EditorDadosCurriculo.jsx";

const DADOS_CURRICULO_VAZIOS = {
  nome_completo: "",
  titulo_profissional: "",
  contato: { email: "", telefone: "", linkedin: "", cidade: "" },
  resumo_profissional: "",
  experiencias: [],
  formacao: [],
  habilidades_tecnicas: [],
  idiomas: [],
  certificacoes: [],
  secoes_adicionais: [],
};

export default function UploadCurriculo() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = lerSessao()?.email || searchParams.get("email") || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [arquivo, setArquivo] = useState(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [curriculosSalvos, setCurriculosSalvos] = useState([]);
  const [curriculoSelecionado, setCurriculoSelecionado] = useState(null);
  const [modoCadastro, setModoCadastro] = useState("arquivo");
  const [dadosRevisao, setDadosRevisao] = useState(null);
  const [nomeCurriculoRevisao, setNomeCurriculoRevisao] = useState("");
  const [salvandoRevisao, setSalvandoRevisao] = useState(false);
  const [abaModal, setAbaModal] = useState("original");
  const [dadosModal, setDadosModal] = useState(null);
  const [carregandoEdicaoModal, setCarregandoEdicaoModal] = useState(false);
  const [salvandoEdicaoModal, setSalvandoEdicaoModal] = useState(false);
  const [blobPreviewEditada, setBlobPreviewEditada] = useState(null);
  const [carregandoPreviewEditada, setCarregandoPreviewEditada] = useState(false);

  useEffect(() => {
    if (!emailInicial) return;
    listarCurriculos(emailInicial)
      .then((resposta) => setCurriculosSalvos(resposta.curriculos || []))
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setErro("Não encontramos um usuário cadastrado com esse e-mail.");
        }
      });
  }, [emailInicial]);

  function entrarComEmail(evento) {
    evento.preventDefault();
    setSearchParams({ email: emailCampo });
  }

  function selecionarArquivo(file) {
    setDadosRevisao(null);
    const mensagemErro = validarArquivoCurriculo(file);
    if (mensagemErro) {
      setErro(mensagemErro);
      setArquivo(null);
      return;
    }
    setErro("");
    setArquivo(file);
  }

  function aoSoltarArquivo(evento) {
    evento.preventDefault();
    setArrastando(false);
    const file = evento.dataTransfer.files?.[0];
    if (file) selecionarArquivo(file);
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    if (!arquivo) return;
    setErro("");
    setEnviando(true);
    try {
      const resposta = await previsualizarCurriculo(emailInicial, arquivo);
      setDadosRevisao(resposta.dados || DADOS_CURRICULO_VAZIOS);
      setNomeCurriculoRevisao(resposta.nome_arquivo.replace(/\.[^.]+$/, ""));
      setModoCadastro("arquivo");
      setSucesso("Leitura concluída. Confira os dados reconhecidos e corrija o que for necessário.");
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível ler e preparar a revisão do currículo.");
    } finally {
      setEnviando(false);
    }
  }

  async function salvarRevisao(dados) {
    setErro("");
    setSucesso("");
    setSalvandoRevisao(true);
    try {
      if (modoCadastro === "manual") {
        const resposta = await criarCurriculoManual(emailInicial, {
          ...dados,
          nome_curriculo: dados.nome_curriculo,
        });
        const curriculos = (await listarCurriculos(emailInicial)).curriculos || [];
        setCurriculosSalvos(curriculos);
        setSucesso("Currículo cadastrado. Os dados estão salvos e prontos para análise ou exportação.");
        setDadosRevisao(null);
        setModoCadastro("arquivo");
      } else if (arquivo && dadosRevisao) {
        await enviarCurriculo(emailInicial, arquivo, dados);
        const curriculos = (await listarCurriculos(emailInicial)).curriculos || [];
        setCurriculosSalvos(curriculos);
        setSucesso("Currículo revisado e salvo. Os dados confirmados estão prontos para análise ou exportação.");
        setArquivo(null);
        setDadosRevisao(null);
      } else {
        setErro("Leia um arquivo antes de salvar o currículo.");
        return;
      }
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível salvar os dados do currículo.");
    } finally {
      setSalvandoRevisao(false);
    }
  }

  function iniciarCadastroManual() {
    setErro("");
    setSucesso("");
    setArquivo(null);
    setNomeCurriculoRevisao("Meu currículo");
    setDadosRevisao(DADOS_CURRICULO_VAZIOS);
    setModoCadastro("manual");
  }

  async function excluirDaLista(curriculo) {
    if (!window.confirm(`Excluir o currículo "${curriculo.nome_curriculo || curriculo.nome_arquivo}"?`)) return;
    try {
      setErro("");
      await excluirCurriculo(curriculo.id_curriculo, emailInicial);
      setCurriculosSalvos((atuais) => atuais.filter((item) => item.id_curriculo !== curriculo.id_curriculo));
      if (curriculoSelecionado?.id_curriculo === curriculo.id_curriculo) fecharCurriculoOriginal();
      setSucesso("Currículo excluído.");
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível excluir o currículo.");
    }
  }

  function abrirCurriculoOriginal(curriculo) {
    setErro("");
    setSucesso("");
    setCurriculoSelecionado(curriculo);
    setAbaModal(curriculo.possui_edicao ? "editada" : "original");
    setDadosModal(null);
    setBlobPreviewEditada(null);
    setCarregandoEdicaoModal(false);
    if (curriculo.possui_edicao) {
      gerarPreviewEditada(curriculo.id_curriculo);
    }
  }

  function fecharCurriculoOriginal() {
    setCurriculoSelecionado(null);
    setDadosModal(null);
    setBlobPreviewEditada(null);
    setErro("");
    setSucesso("");
  }

  async function abrirEditorModal() {
    if (!curriculoSelecionado) return;
    setErro("");
    setCarregandoEdicaoModal(true);
    try {
      const resposta = await obterEdicaoCurriculo(curriculoSelecionado.id_curriculo, emailInicial);
      setDadosModal(resposta.dados || DADOS_CURRICULO_VAZIOS);
      setNomeCurriculoRevisao(curriculoSelecionado.nome_curriculo || curriculoSelecionado.nome_arquivo.replace(/\.[^.]+$/, ""));
      setAbaModal("editar");
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível carregar os dados para edição.");
    } finally {
      setCarregandoEdicaoModal(false);
    }
  }

  async function gerarPreviewEditada(idCurriculo = curriculoSelecionado?.id_curriculo) {
    if (!idCurriculo) return false;
    setErro("");
    setCarregandoPreviewEditada(true);
    try {
      const { blob } = await exportarCurriculo(emailInicial, idCurriculo, "generico", "pdf", "editada");
      setBlobPreviewEditada(blob);
      setAbaModal("editada");
      return true;
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível gerar a pré-visualização editada.");
      return false;
    } finally {
      setCarregandoPreviewEditada(false);
    }
  }

  async function salvarEdicaoModal(dados) {
    if (!curriculoSelecionado) return;
    setErro("");
    setSalvandoEdicaoModal(true);
    try {
      const resposta = await salvarEdicaoEstruturada(
        curriculoSelecionado.id_curriculo,
        emailInicial,
        dados,
      );
      setDadosModal(resposta.dados || dados);
      const lista = (await listarCurriculos(emailInicial)).curriculos || [];
      setCurriculosSalvos(lista);
      const curriculoAtualizado = lista.find((item) => item.id_curriculo === curriculoSelecionado.id_curriculo);
      if (curriculoAtualizado) {
        setCurriculoSelecionado((atual) => ({ ...atual, ...curriculoAtualizado }));
      }
      const previewGerada = await gerarPreviewEditada(curriculoSelecionado.id_curriculo);
      setSucesso(
        previewGerada
          ? "Alterações salvas. A análise e as próximas exportações usarão os dados revisados."
          : "Alterações salvas; não foi possível gerar a prévia agora. Tente novamente.",
      );
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível salvar as alterações do currículo.");
    } finally {
      setSalvandoEdicaoModal(false);
    }
  }

  function baixarPreviewEditada() {
    if (!blobPreviewEditada || !curriculoSelecionado) return;
    const url = URL.createObjectURL(blobPreviewEditada);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${curriculoSelecionado.nome_curriculo || "curriculo"} - revisado.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function baixarCurriculoSelecionado() {
    if (!curriculoSelecionado) return;
    try {
      const { blob, nomeArquivo } = await baixarArquivoCurriculo(
        curriculoSelecionado.id_curriculo,
        emailInicial,
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = nomeArquivo || curriculoSelecionado.nome_arquivo;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível baixar este currículo.");
    }
  }

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="curriculo" />

      <main className="flex-1 p-6 space-y-6 md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Enviar currículo</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Faça o upload do seu currículo em PDF ou DOCX para guardá-lo no sistema e visualizá-lo sempre que precisar.
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

        {erro && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">{erro}</div>}
        {sucesso && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-700">{sucesso}</div>
        )}
        {emailInicial && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-6">
            <div className="flex items-center gap-3">
              <i className="ti ti-file-upload text-[28px] text-[#1e5e3f]"></i>
              <h2 className="font-brand text-[28px] text-black">Novo currículo</h2>
            </div>

            <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-4">
              <button
                type="button"
                onClick={() => {
                  setModoCadastro("arquivo");
                  setDadosRevisao(null);
                  setErro("");
                  setSucesso("");
                }}
                className={`rounded-md px-4 py-2 text-sm font-semibold ${modoCadastro === "arquivo" ? "bg-[#1e5e3f] text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
              >
                <i className="ti ti-upload mr-1.5"></i>Enviar arquivo
              </button>
              <button
                type="button"
                onClick={iniciarCadastroManual}
                className={`rounded-md px-4 py-2 text-sm font-semibold ${modoCadastro === "manual" ? "bg-[#1e5e3f] text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
              >
                <i className="ti ti-edit mr-1.5"></i>Preencher manualmente
              </button>
            </div>

            {modoCadastro === "arquivo" && (
            <form onSubmit={aoEnviar} className="space-y-4">
              <label
                htmlFor="input-arquivo"
                onDragOver={(e) => {
                  e.preventDefault();
                  setArrastando(true);
                }}
                onDragLeave={() => setArrastando(false)}
                onDrop={aoSoltarArquivo}
                className={`flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-10 text-center cursor-pointer transition-colors ${
                  arrastando ? "border-[#1e5e3f] bg-[#f0fdf4]" : "border-[#dfdfe0] hover:border-[#1e5e3f] hover:bg-[#f7f7f7]"
                }`}
              >
                <input
                  type="file"
                  id="input-arquivo"
                  accept=".pdf,.docx"
                  className="hidden"
                  onChange={(e) => selecionarArquivo(e.target.files?.[0])}
                />
                {!arquivo && (
                  <>
                    <i className="ti ti-cloud-upload text-[40px] text-[#1e5e3f]"></i>
                    <p className="font-brand text-lg font-semibold text-[#595859]">Clique para selecionar</p>
                    <p className="text-sm text-gray-400">ou arraste e solte seu arquivo aqui (PDF, DOCX até 5MB)</p>
                  </>
                )}
                {arquivo && (
                  <>
                    <i className="ti ti-circle-check text-[40px] text-[#1e5e3f]"></i>
                    <p className="font-brand text-lg font-semibold text-[#595859] break-all px-4">{arquivo.name}</p>
                    <p className="text-sm text-gray-400">{formatarTamanhoArquivo(arquivo.size)}</p>
                    <p className="text-sm text-[#1e5e3f] font-medium">Clique novamente para trocar de arquivo</p>
                  </>
                )}
              </label>

              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={!arquivo || enviando}
                  className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-5 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60 transition-colors"
                >
                  <i className={`ti ${enviando ? "ti-loader animate-spin" : "ti-search"}`}></i>
                  {enviando ? "Lendo currículo..." : "Ler e revisar"}
                </button>
              </div>
              {enviando && (
                <div
                  className="flex items-center gap-4 rounded-xl border border-[#1e5e3f]/20 bg-[#f0fdf4] px-5 py-4"
                  role="status"
                  aria-live="polite"
                >
                  <div className="relative flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-[#1e5e3f]/20 bg-white">
                    <i className="ti ti-file-text text-2xl text-[#1e5e3f]"></i>
                    <span className="curriculo-scan-line" aria-hidden="true"></span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-[#174a32]">Estamos lendo seu currículo</p>
                    <p className="mt-0.5 text-sm text-gray-600">Extraindo e organizando as informações para você revisar.</p>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#1e5e3f]/10">
                      <div className="curriculo-loading-bar h-full w-2/5 rounded-full bg-[#1e5e3f]"></div>
                    </div>
                  </div>
                </div>
              )}
            </form>
            )}

            {dadosRevisao && (
              <div className="space-y-4">
                <div>
                  <h3 className="font-brand text-xl font-bold text-black">
                    {modoCadastro === "manual" ? "Preencha os dados do currículo" : "Confira os dados reconhecidos"}
                  </h3>
                  <p className="mt-1 text-sm text-gray-600">
                    {modoCadastro === "manual"
                      ? "Preencha as informações que deseja incluir. Você poderá revisar tudo antes de salvar."
                      : "Revise os campos preenchidos automaticamente. Corrija ou complete as informações antes de usar o currículo."}
                  </p>
                </div>
                {modoCadastro === "arquivo" && (() => {
                  const ausentes = [
                    !dadosRevisao.nome_completo && "nome completo",
                    !dadosRevisao.resumo_profissional && "resumo profissional",
                    !dadosRevisao.experiencias?.length && "experiências profissionais",
                    !dadosRevisao.formacao?.length && "formação",
                  ].filter(Boolean);
                  return ausentes.length > 0 ? (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                      <strong>Confira com atenção:</strong> não identificamos {ausentes.join(", ")}. Preencha esses campos se eles constarem no seu currículo.
                    </div>
                  ) : null;
                })()}
                <EditorDadosCurriculo
                  key={`${modoCadastro}-${arquivo?.name || "manual"}`}
                  dados={dadosRevisao}
                  nomeCurriculo={nomeCurriculoRevisao}
                  onSalvar={salvarRevisao}
                  salvando={salvandoRevisao}
                  textoBotao="Salvar currículo"
                />
              </div>
            )}
          </div>
        )}

        {/* Lista de currículos salvos - similar à lista de vagas salvas em NovaVaga */}
        {emailInicial && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <i className="ti ti-files text-[24px] text-[#1e5e3f]"></i>
                <h2 className="font-brand text-2xl font-bold text-black">Seus currículos salvos</h2>
              </div>
              {curriculosSalvos.length > 0 && (
                <span className="text-xs font-semibold px-2.5 py-1 bg-gray-200 text-gray-700 rounded-full">
                  {curriculosSalvos.length} {curriculosSalvos.length === 1 ? "currículo" : "currículos"}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500">
              Clique em um currículo para visualizar o arquivo original.
            </p>

            {curriculosSalvos.length > 0 && (
              <ul className="space-y-3">
                {curriculosSalvos.map((curr) => (
                  <li key={curr.id_curriculo}>
                    <div
                      onClick={() => abrirCurriculoOriginal(curr)}
                      className="w-full flex items-center justify-between p-4 rounded-lg border-[0.5px] border-black bg-white hover:border-[#1e5e3f] hover:shadow-sm cursor-pointer transition-all"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-lg bg-[#f0fdf4] border border-[#1e5e3f]/20 flex items-center justify-center flex-shrink-0">
                          <i className="ti ti-file-text text-[22px] text-[#1e5e3f]"></i>
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium text-black truncate">{curr.nome_arquivo}</p>
                          <p className="text-xs text-gray-500">
                            Enviado em {formatarDataUpload(curr.data_upload)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                          <i className="ti ti-check text-[14px]"></i> {curr.status_processamento === "concluido" ? "Salvo" : curr.status_processamento}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            abrirCurriculoOriginal(curr);
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-[#1e5e3f] bg-[#f0fdf4] hover:bg-[#e0f7ea] border border-[#1e5e3f]/30 rounded-md transition-colors"
                        >
                          <i className="ti ti-eye text-[16px]"></i> Abrir
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            excluirDaLista(curr);
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-md transition-colors"
                        >
                          <i className="ti ti-trash text-[16px]"></i> Excluir
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {curriculosSalvos.length === 0 && (
              <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-gray-500 space-y-1">
                <i className="ti ti-file-off text-[32px] text-gray-400"></i>
                <p className="font-medium text-gray-700">Nenhum currículo salvo ainda.</p>
                <p className="text-xs">Faça o upload do seu primeiro arquivo no campo acima para guardá-lo no sistema.</p>
              </div>
            )}
          </div>
        )}

        {/* Modal / Visualizador de Currículo */}
        {curriculoSelecionado && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
            <div className="relative w-full max-w-3xl max-h-[90vh] flex flex-col rounded-xl border border-gray-200 bg-white shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              {/* Cabeçalho */}
              <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 bg-gray-50">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-[#f0fdf4] border border-[#1e5e3f]/20 flex items-center justify-center flex-shrink-0">
                    <i className="ti ti-file-description text-[24px] text-[#1e5e3f]"></i>
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-brand text-lg font-bold text-black truncate">
                      {curriculoSelecionado.nome_arquivo}
                    </h3>
                    <p className="text-xs text-gray-500">
                      Enviado em {formatarDataUpload(curriculoSelecionado.data_upload)}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={fecharCurriculoOriginal}
                  className="rounded-lg p-2 text-gray-400 hover:bg-gray-200 hover:text-black transition-colors"
                  aria-label="Fechar"
                >
                  <i className="ti ti-x text-[20px]"></i>
                </button>
              </div>

              {(curriculoSelecionado.possui_edicao || curriculoSelecionado.possui_arquivo) && (
                <div className="flex gap-2 border-b border-gray-200 bg-white px-6 py-3">
                  {curriculoSelecionado.possui_edicao && (
                    <button
                      type="button"
                      onClick={() => gerarPreviewEditada()}
                      disabled={carregandoPreviewEditada}
                      className={`rounded-md px-3 py-2 text-sm font-semibold disabled:opacity-60 ${abaModal === "editada" ? "bg-[#1e5e3f] text-white" : "bg-[#f0fdf4] text-[#1e5e3f] hover:bg-[#e0f7ea]"}`}
                    >
                      {carregandoPreviewEditada ? "Gerando prévia..." : "Versão revisada"}
                    </button>
                  )}
                  {curriculoSelecionado.possui_arquivo && (
                    <button
                      type="button"
                      onClick={() => setAbaModal("original")}
                      className={`rounded-md px-3 py-2 text-sm font-semibold ${abaModal === "original" ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                    >
                      Arquivo original
                    </button>
                  )}
                </div>
              )}

              {erro && (
                <div role="alert" className="mx-5 mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {erro}
                </div>
              )}

              {sucesso && (
                <div className="mx-5 mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
                  {sucesso}
                </div>
              )}

              {/* Conteúdo: a prévia revisada é gerada separadamente; o PDF original permanece intacto. */}
              <div className="flex-1 min-h-0 overflow-y-auto bg-gray-100">
                {abaModal === "editar" ? (
                  carregandoEdicaoModal || !dadosModal ? (
                    <div className="py-12 text-center text-gray-500">
                      <i className="ti ti-loader animate-spin text-2xl text-[#1e5e3f]"></i>
                      <p className="mt-2 text-sm">Carregando dados do currículo...</p>
                    </div>
                  ) : (
                    <div className="bg-white p-5 sm:p-7">
                      <EditorDadosCurriculo
                        key={curriculoSelecionado.id_curriculo}
                        dados={dadosModal}
                        nomeCurriculo={curriculoSelecionado.nome_curriculo || curriculoSelecionado.nome_arquivo.replace(/\.[^.]+$/, "")}
                        onSalvar={salvarEdicaoModal}
                        salvando={salvandoEdicaoModal}
                        textoBotao="Salvar"
                      />
                    </div>
                  )
                ) : abaModal === "editada" ? (
                  blobPreviewEditada ? (
                    <LimiteDeErro chave={`${curriculoSelecionado.id_curriculo}-editada`}>
                      <VisualizadorPdf blob={blobPreviewEditada} />
                    </LimiteDeErro>
                  ) : (
                    <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center text-gray-600">
                      <i className="ti ti-file-description text-[40px] text-[#1e5e3f]"></i>
                      <p className="font-semibold">A prévia revisada é um documento separado do arquivo original.</p>
                      <button
                        type="button"
                        onClick={() => gerarPreviewEditada()}
                        disabled={carregandoPreviewEditada}
                        className="rounded-md bg-[#1e5e3f] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                      >
                        {carregandoPreviewEditada ? "Gerando..." : "Gerar prévia revisada"}
                      </button>
                    </div>
                  )
                ) : curriculoSelecionado.possui_arquivo && curriculoSelecionado.nome_arquivo?.toLowerCase().endsWith(".pdf") ? (
                  <LimiteDeErro chave={curriculoSelecionado.id_curriculo}>
                    <VisualizadorPdf idCurriculo={curriculoSelecionado.id_curriculo} email={emailInicial} />
                  </LimiteDeErro>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center gap-2 text-center text-gray-500 p-6">
                    <i className="ti ti-file-text text-[32px] text-gray-400"></i>
                    {curriculoSelecionado.possui_arquivo ? (
                      <>
                        <p className="text-sm">Este formato (.docx) não tem pré-visualização própria ainda.</p>
                        <p className="text-xs text-gray-400">Baixe o arquivo original abaixo para abri-lo no Word.</p>
                      </>
                    ) : (
                      <>
                        <p className="text-sm">Este currículo foi preenchido manualmente e ainda não tem arquivo original.</p>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* O download original nunca é substituído pela versão revisada. */}
              <div className="flex items-center justify-between border-t border-gray-200 px-6 py-4 bg-gray-50">
                <div className="flex flex-wrap gap-2">
                  {curriculoSelecionado.possui_arquivo && (
                    <button
                      type="button"
                      onClick={baixarCurriculoSelecionado}
                      className="flex items-center gap-2 rounded-md border border-[#1e5e3f] bg-white px-4 py-2 text-sm font-semibold text-[#1e5e3f] hover:bg-[#f0fdf4] transition-colors"
                    >
                      <i className="ti ti-download"></i> Baixar arquivo original
                    </button>
                  )}
                  {blobPreviewEditada && abaModal === "editada" && (
                    <button
                      type="button"
                      onClick={baixarPreviewEditada}
                      className="flex items-center gap-2 rounded-md border border-[#1e5e3f] bg-white px-4 py-2 text-sm font-semibold text-[#1e5e3f] hover:bg-[#f0fdf4]"
                    >
                      <i className="ti ti-download"></i> Baixar versão revisada
                    </button>
                  )}
                </div>
                <div className="flex gap-2">
                  {abaModal !== "editar" && (
                    <button
                      type="button"
                      onClick={abrirEditorModal}
                      disabled={carregandoEdicaoModal}
                      className="rounded-md bg-[#1e5e3f] px-4 py-2 text-sm font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                    >
                      <i className="ti ti-edit mr-1.5"></i>Editar currículo
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={fecharCurriculoOriginal}
                    className="rounded-md bg-gray-800 px-5 py-2 text-sm font-semibold text-white hover:bg-black transition-colors"
                  >
                    Fechar
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
