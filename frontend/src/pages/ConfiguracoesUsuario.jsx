import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import {
  atualizarPerfilUsuario as salvarPerfil,
  cancelarExclusaoConta,
  confirmarExclusaoConta,
  obterPerfilUsuario,
  obterStatusExclusaoConta,
  solicitarExclusaoConta,
} from "../api/authApi.js";
import { ApiError } from "../api/client.js";
import { lerSessao, limparSessao, salvarSessao } from "../models/usuario.js";

export default function ConfiguracoesUsuario() {
  const navigate = useNavigate();
  const sessaoInicial = lerSessao();
  const [perfil, setPerfil] = useState(null);
  const [statusExclusao, setStatusExclusao] = useState(null);
  const [nome, setNome] = useState("");
  const [notificacoesPorEmail, setNotificacoesPorEmail] = useState(true);
  const [carregando, setCarregando] = useState(Boolean(sessaoInicial?.accessToken));
  const [salvando, setSalvando] = useState(false);
  const [acaoExclusao, setAcaoExclusao] = useState("");
  const [confirmandoSolicitacao, setConfirmandoSolicitacao] = useState(false);
  const [confirmacaoDigitada, setConfirmacaoDigitada] = useState("");
  const [contaExcluida, setContaExcluida] = useState(false);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");

  useEffect(() => {
    if (!sessaoInicial?.accessToken) return;

    Promise.all([obterPerfilUsuario(), obterStatusExclusaoConta()])
      .then(([dados, status]) => {
        setPerfil(dados);
        setNome(dados.nome);
        setNotificacoesPorEmail(dados.notificacoes_por_email);
        setStatusExclusao(status);
      })
      .catch((falha) => {
        setErro(
          falha instanceof ApiError
            ? falha.message
            : "Não foi possível carregar as configurações. Tente novamente.",
        );
      })
      .finally(() => setCarregando(false));
  }, []);

  async function aoSalvarConfiguracoes(evento) {
    evento.preventDefault();
    setErro("");
    setMensagem("");
    setSalvando(true);

    try {
      const perfilAtualizado = await salvarPerfil({
        nome: nome.trim(),
        notificacoes_por_email: notificacoesPorEmail,
      });
      setPerfil(perfilAtualizado);
      setNome(perfilAtualizado.nome);
      setNotificacoesPorEmail(perfilAtualizado.notificacoes_por_email);

      const sessaoAtual = lerSessao();
      if (sessaoAtual) {
        salvarSessao({ ...sessaoAtual, nome: perfilAtualizado.nome, email: perfilAtualizado.email });
      }

      setMensagem("Configurações salvas com sucesso.");
    } catch (falha) {
      setErro(
        falha instanceof ApiError
          ? falha.message
          : "Não foi possível salvar as configurações. Tente novamente.",
      );
    } finally {
      setSalvando(false);
    }
  }

  async function executarAcaoExclusao(tipo, acao) {
    setErro("");
    setMensagem("");
    setAcaoExclusao(tipo);

    try {
      const resposta = await acao();
      if (tipo === "solicitar") {
        setStatusExclusao(await obterStatusExclusaoConta());
        setConfirmandoSolicitacao(false);
      } else if (tipo === "cancelar") {
        setStatusExclusao({ solicitada: false });
        setConfirmacaoDigitada("");
        setMensagem(resposta.mensagem);
      } else {
        limparSessao();
        setContaExcluida(true);
        setPerfil(null);
        setStatusExclusao({ solicitada: false });
        setMensagem("Conta excluída. Os dados vinculados a ela foram removidos do sistema.");
      }
    } catch (falha) {
      setErro(
        falha instanceof ApiError
          ? falha.message
          : "Não foi possível concluir a ação. Tente novamente.",
      );
    } finally {
      setAcaoExclusao("");
    }
  }

  function formatarDataExpiracao(data) {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "long",
      timeStyle: "short",
    }).format(new Date(data));
  }

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={contaExcluida ? "" : perfil?.email || sessaoInicial?.email} ativo="" />

      <main className="flex-1 p-6 space-y-6 md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Configurações da conta</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Atualize seus dados de perfil e suas preferências de e-mail.
          </p>
        </div>

        {erro && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">{erro}</div>}

        {contaExcluida ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-6 text-green-800">
            <p role="status" className="font-semibold">{mensagem}</p>
            <p className="mt-2 text-sm">
              Você saiu da conta. Para usar o serviço novamente, será necessário criar uma nova conta.
            </p>
            <Link to="/" className="mt-4 inline-flex font-semibold underline">Voltar ao início</Link>
          </div>
        ) : !sessaoInicial?.accessToken ? (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-6">
            <p className="text-lg font-medium text-gray-700">Faça login para acessar as configurações da sua conta.</p>
            <Link
              to="/login"
              className="mt-4 inline-flex items-center rounded-md bg-[#1e5e3f] px-4 py-2 font-bold text-white hover:bg-[#174a32]"
            >
              Fazer login
            </Link>
          </div>
        ) : carregando ? (
          <p role="status" className="text-gray-600">Carregando configurações...</p>
        ) : perfil ? (
          <form onSubmit={aoSalvarConfiguracoes} className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label htmlFor="nome" className="mb-1 block text-sm font-medium text-[#595859]">
                  Nome de exibição
                </label>
                <input
                  id="nome"
                  type="text"
                  maxLength={150}
                  required
                  value={nome}
                  onChange={(evento) => setNome(evento.target.value)}
                  className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
                />
              </div>

              <div>
                <label htmlFor="email" className="mb-1 block text-sm font-medium text-[#595859]">
                  E-mail da conta
                </label>
                <input
                  id="email"
                  type="email"
                  value={perfil.email}
                  readOnly
                  className="w-full rounded border border-[#dfdfe0] bg-[#f7f7f7] px-3 py-2 text-sm text-gray-500"
                />
              </div>
            </div>

            <div className="rounded-lg border border-[#dfdfe0] bg-[#f8faf9] p-4">
              <label className="flex cursor-pointer items-center justify-between gap-4 text-sm font-medium text-[#2b2b2b]">
                <span>Receber alertas por e-mail</span>
                <input
                  type="checkbox"
                  checked={notificacoesPorEmail}
                  onChange={(evento) => setNotificacoesPorEmail(evento.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-[#1e5e3f] focus:ring-[#1e5e3f]"
                />
              </label>
            </div>

            {mensagem && (
              <div role="status" className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-700">
                {mensagem}
              </div>
            )}

            <button
              type="submit"
              disabled={salvando}
              className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
            >
              <i className="ti ti-device-floppy"></i> {salvando ? "Salvando..." : "Salvar configurações"}
            </button>

            <section aria-labelledby="excluir-conta-titulo" className="border-t border-red-200 pt-6">
              <h2 id="excluir-conta-titulo" className="font-brand text-xl font-bold text-red-800">
                Excluir conta e dados
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-700">
                Você pode solicitar a exclusão dos seus dados pessoais. A exclusão é permanente e remove sua
                conta, currículos, vagas, análises, conversas e simulações vinculados a ela. Após solicitar,
                você terá até 48 horas para confirmar a exclusão definitiva ou cancelar o pedido. Se o prazo
                passar sem confirmação, o pedido expira e a conta permanece ativa. Dados que precisem ser
                mantidos por obrigação legal podem estar sujeitos às exceções previstas na legislação.
              </p>

              {statusExclusao?.solicitada ? (
                <div className="mt-4 space-y-4 rounded-lg border border-amber-300 bg-amber-50 p-4">
                  <p className="text-sm text-amber-950">
                    Solicitação pendente. Confirme ou cancele até{" "}
                    <strong>{formatarDataExpiracao(statusExclusao.expira_em)}</strong>.
                  </p>
                  <div className="max-w-md space-y-2">
                    <label htmlFor="confirmar-exclusao" className="block text-sm font-medium text-red-900">
                      Para excluir definitivamente, digite EXCLUIR
                    </label>
                    <input
                      id="confirmar-exclusao"
                      type="text"
                      autoComplete="off"
                      value={confirmacaoDigitada}
                      onChange={(evento) => setConfirmacaoDigitada(evento.target.value)}
                      className="w-full rounded border border-red-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-700"
                    />
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <button
                      type="button"
                      disabled={Boolean(acaoExclusao) || confirmacaoDigitada.trim() !== "EXCLUIR"}
                      onClick={() =>
                        executarAcaoExclusao("confirmar", confirmarExclusaoConta)
                      }
                      className="rounded-md bg-red-700 px-4 py-2 font-bold text-white hover:bg-red-800 disabled:opacity-60"
                    >
                      {acaoExclusao === "confirmar" ? "Excluindo..." : "Excluir permanentemente"}
                    </button>
                    <button
                      type="button"
                      disabled={Boolean(acaoExclusao)}
                      onClick={() => executarAcaoExclusao("cancelar", cancelarExclusaoConta)}
                      className="rounded-md border border-gray-400 px-4 py-2 font-semibold text-gray-800 hover:bg-white disabled:opacity-60"
                    >
                      {acaoExclusao === "cancelar" ? "Cancelando..." : "Cancelar solicitação"}
                    </button>
                  </div>
                </div>
              ) : confirmandoSolicitacao ? (
                <div className="mt-4 max-w-2xl rounded-lg border border-red-300 bg-red-50 p-4">
                  <p className="text-sm leading-6 text-red-950">
                    A solicitação inicia o prazo de 48 horas. Seus dados só serão removidos depois de uma
                    segunda confirmação explícita. Deseja registrar a solicitação?
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      type="button"
                      disabled={Boolean(acaoExclusao)}
                      onClick={() => executarAcaoExclusao("solicitar", solicitarExclusaoConta)}
                      className="rounded-md bg-red-700 px-4 py-2 font-bold text-white hover:bg-red-800 disabled:opacity-60"
                    >
                      {acaoExclusao === "solicitar" ? "Registrando..." : "Sim, solicitar exclusão"}
                    </button>
                    <button
                      type="button"
                      disabled={Boolean(acaoExclusao)}
                      onClick={() => setConfirmandoSolicitacao(false)}
                      className="rounded-md border border-gray-400 px-4 py-2 font-semibold text-gray-800 hover:bg-white disabled:opacity-60"
                    >
                      Voltar
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmandoSolicitacao(true)}
                  className="mt-4 rounded-md border border-red-700 px-4 py-2 font-bold text-red-800 hover:bg-red-50"
                >
                  Solicitar exclusão da conta
                </button>
              )}
            </section>
          </form>
        ) : null}
      </main>
    </div>
  );
}
