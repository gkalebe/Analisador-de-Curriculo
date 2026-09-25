import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import VisualizadorPdf from "../components/VisualizadorPdf.jsx";
import LimiteDeErro from "../components/LimiteDeErro.jsx";
import {
  atualizarCurriculo,
  enviarCurriculo,
  listarCurriculos,
  obterDetalhesCurriculo,
  obterUrlDownloadCurriculo,
} from "../api/curriculoApi.js";
import {
  formatarDataUpload,
  formatarTamanhoArquivo,
  validarArquivoCurriculo,
} from "../models/curriculo.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

export default function UploadCurriculo() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || lerSessao()?.email || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [arquivo, setArquivo] = useState(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [resultado, setResultado] = useState(null);
  const [curriculosSalvos, setCurriculosSalvos] = useState([]);
  const [curriculoSelecionado, setCurriculoSelecionado] = useState(null);
  const [curriculoDetalhes, setCurriculoDetalhes] = useState(null);
  const [editandoCurriculo, setEditandoCurriculo] = useState(false);
  const [dadosCurriculo, setDadosCurriculo] = useState({
    nome: "",
    email: "",
    telefone: "",
    resumo: "",
    formacao: "",
    experiencia_profissional: "",
    habilidades: "",
  });
  const [salvandoCurriculo, setSalvandoCurriculo] = useState(false);

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
    setResultado(null);
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
      const resposta = await enviarCurriculo(emailInicial, arquivo);
      setResultado(resposta);
      setArquivo(null);
      const listaAtualizada = await listarCurriculos(emailInicial);
      setCurriculosSalvos(listaAtualizada.curriculos || []);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível enviar o currículo. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  }

  async function abrirCurriculoOriginal(curriculo) {
    setErro("");
    setSucesso("");
    setCurriculoSelecionado(curriculo);
    setEditandoCurriculo(false);
    setCurriculoDetalhes(null);
    try {
      const detalhes = await obterDetalhesCurriculo(curriculo.id_curriculo, emailInicial);
      setCurriculoDetalhes(detalhes);
      setDadosCurriculo({
        nome: detalhes?.dados?.nome || "",
        email: detalhes?.dados?.email || "",
        telefone: detalhes?.dados?.telefone || "",
        resumo: detalhes?.dados?.resumo || "",
        formacao: detalhes?.dados?.formacao || "",
        experiencia_profissional: detalhes?.dados?.experiencia_profissional || "",
        habilidades: detalhes?.dados?.habilidades || "",
      });
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível carregar o currículo.");
    }
  }

  function fecharCurriculoOriginal() {
    setCurriculoSelecionado(null);
    setCurriculoDetalhes(null);
    setEditandoCurriculo(false);
    setErro("");
    setSucesso("");
  }

  async function salvarEdicaoCurriculo(evento) {
    evento.preventDefault();
    if (!curriculoSelecionado) return;

    try {
      setErro("");
      setSucesso("");
      setSalvandoCurriculo(true);
      const atualizado = await atualizarCurriculo(curriculoSelecionado.id_curriculo, emailInicial, dadosCurriculo);
      setCurriculoDetalhes(atualizado);
      setDadosCurriculo({
        nome: atualizado?.dados?.nome || "",
        email: atualizado?.dados?.email || "",
        telefone: atualizado?.dados?.telefone || "",
        resumo: atualizado?.dados?.resumo || "",
        formacao: atualizado?.dados?.formacao || "",
        experiencia_profissional: atualizado?.dados?.experiencia_profissional || "",
        habilidades: atualizado?.dados?.habilidades || "",
      });
      setEditandoCurriculo(false);
      setSucesso("Currículo atualizado com sucesso.");
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível atualizar este currículo.");
    } finally {
      setSalvandoCurriculo(false);
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
        {resultado && !sucesso && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-700">
            Currículo <strong>{resultado.nome_arquivo}</strong> enviado e salvo com sucesso.
          </div>
        )}

        {emailInicial && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-6">
            <div className="flex items-center gap-3">
              <i className="ti ti-file-upload text-[28px] text-[#1e5e3f]"></i>
              <h2 className="font-brand text-[28px] text-black">Novo currículo</h2>
            </div>

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

              <button
                type="submit"
                disabled={!arquivo || enviando}
                className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-5 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60 transition-colors"
              >
                <i className="ti ti-send"></i> {enviando ? "Enviando e salvando..." : "Salvar currículo"}
              </button>
            </form>
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
            <div className="relative w-full max-w-3xl max-h-[90vh] flex flex-col rounded-xl border border-black bg-white shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
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

              <div className="flex-1 min-h-0 overflow-y-auto bg-gray-100">
                {!editandoCurriculo ? (
                  <div className="space-y-4 p-6">
                    <div className="rounded-lg border border-[#dfdfe0] bg-white p-4">
                      <div className="mb-3 flex items-center justify-between">
                        <h4 className="font-brand text-xl text-black">Dados do currículo</h4>
                        <button
                          type="button"
                          onClick={() => setEditandoCurriculo(true)}
                          className="rounded-md border border-[#1e5e3f] bg-[#f0fdf4] px-3 py-1.5 text-sm font-semibold text-[#1e5e3f]"
                        >
                          Editar
                        </button>
                      </div>

                      {curriculoDetalhes?.dados ? (
                        <div className="space-y-3 text-sm text-gray-700">
                          <p><span className="font-semibold">Nome:</span> {curriculoDetalhes.dados.nome || "-"}</p>
                          <p><span className="font-semibold">Email:</span> {curriculoDetalhes.dados.email || "-"}</p>
                          <p><span className="font-semibold">Telefone:</span> {curriculoDetalhes.dados.telefone || "-"}</p>
                          <p><span className="font-semibold">Resumo:</span> {curriculoDetalhes.dados.resumo || "-"}</p>
                          <p><span className="font-semibold">Formação:</span> {curriculoDetalhes.dados.formacao || "-"}</p>
                          <p><span className="font-semibold">Experiência:</span> {curriculoDetalhes.dados.experiencia_profissional || "-"}</p>
                          <p><span className="font-semibold">Habilidades:</span> {curriculoDetalhes.dados.habilidades || "-"}</p>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">Ainda não há dados estruturados para este currículo.</p>
                      )}
                    </div>

                    {curriculoSelecionado.nome_arquivo?.toLowerCase().endsWith(".pdf") ? (
                      <LimiteDeErro chave={curriculoSelecionado.id_curriculo}>
                        <VisualizadorPdf idCurriculo={curriculoSelecionado.id_curriculo} email={emailInicial} />
                      </LimiteDeErro>
                    ) : (
                      <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 bg-white text-center text-gray-500 p-6">
                        <i className="ti ti-file-text text-[32px] text-gray-400"></i>
                        <p className="text-sm">
                          Este formato (.docx) não tem pré-visualização própria ainda.
                        </p>
                        <p className="text-xs text-gray-400">Baixe o arquivo original abaixo para abri-lo no Word.</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <form onSubmit={salvarEdicaoCurriculo} className="space-y-4 p-6">
                    <div className="flex items-center justify-between">
                      <h4 className="font-brand text-xl text-black">Editar dados do currículo</h4>
                      <button
                        type="button"
                        onClick={() => setEditandoCurriculo(false)}
                        className="text-sm font-medium text-gray-600 underline"
                      >
                        Cancelar
                      </button>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="space-y-1 text-sm text-gray-700 md:col-span-2">
                        <span className="font-medium">Nome</span>
                        <input value={dadosCurriculo.nome} onChange={(e) => setDadosCurriculo({ ...dadosCurriculo, nome: e.target.value })} className="w-full rounded border border-[#dfdfe0] px-3 py-2" />
                      </label>

                      <label className="space-y-1 text-sm text-gray-700">
                        <span className="font-medium">Email</span>
                        <input type="email" value={dadosCurriculo.email} onChange={(e) => setDadosCurriculo({ ...dadosCurriculo, email: e.target.value })} className="w-full rounded border border-[#dfdfe0] px-3 py-2" />
                      </label>

                      <label className="space-y-1 text-sm text-gray-700">
                        <span className="font-medium">Telefone</span>
                        <input value={dadosCurriculo.telefone} onChange={(e) => setDadosCurriculo({ ...dadosCurriculo, telefone: e.target.value })} className="w-full rounded border border-[#dfdfe0] px-3 py-2" />
                      </label>

                      <label className="space-y-1 text-sm text-gray-700 md:col-span-2">
                        <span className="font-medium">Resumo</span>
                        <textarea rows={4} value={dadosCurriculo.resumo} onChange={(e) => setDadosCurriculo({ ...dadosCurriculo, resumo: e.target.value })} className="w-full rounded border border-[#dfdfe0] px-3 py-2" />
                      </label>

                      <label className="space-y-1 text-sm text-gray-700 md:col-span-2">
                        <span className="font-medium">Formação</span>
                        <textarea rows={3} value={dadosCurriculo.formacao} onChange={(e) => setDadosCurriculo({ ...dadosCurriculo, formacao: e.target.value })} className="w-full rounded border border-[#dfdfe0] px-3 py-2" />
                      </label>

                      <label className="space-y-1 text-sm text-gray-700 md:col-span-2">
                        <span className="font-medium">Experiência profissional</span>
                        <textarea rows={4} value={dadosCurriculo.experiencia_profissional} onChange={(e) => setDadosCurriculo({ ...dadosCurriculo, experiencia_profissional: e.target.value })} className="w-full rounded border border-[#dfdfe0] px-3 py-2" />
                      </label>

                      <label className="space-y-1 text-sm text-gray-700 md:col-span-2">
                        <span className="font-medium">Habilidades</span>
                        <textarea rows={3} value={dadosCurriculo.habilidades} onChange={(e) => setDadosCurriculo({ ...dadosCurriculo, habilidades: e.target.value })} className="w-full rounded border border-[#dfdfe0] px-3 py-2" />
                      </label>
                    </div>

                    <div className="flex justify-end">
                      <button type="submit" disabled={salvandoCurriculo} className="rounded-md bg-[#1e5e3f] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
                        {salvandoCurriculo ? "Salvando..." : "Salvar alterações"}
                      </button>
                    </div>
                  </form>
                )}
              </div>

              {/* Rodapé com Ações */}
              <div className="flex items-center justify-between border-t border-gray-200 px-6 py-4 bg-gray-50">
                <a
                  href={obterUrlDownloadCurriculo(curriculoSelecionado.id_curriculo, emailInicial)}
                  target="_blank"
                  rel="noreferrer"
                  download={curriculoSelecionado.nome_arquivo}
                  className="flex items-center gap-2 rounded-md border border-[#1e5e3f] bg-white px-4 py-2 text-sm font-semibold text-[#1e5e3f] hover:bg-[#f0fdf4] transition-colors"
                >
                  <i className="ti ti-download"></i> Baixar arquivo original
                </a>
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
        )}
      </main>
    </div>
  );
}
