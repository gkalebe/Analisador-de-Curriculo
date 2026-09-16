import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { cadastrarUsuario, login as loginApi } from "../api/authApi.js";
import { criarSessao, salvarSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

const REGEX_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const CAMPO_POR_LOC = {
  nome: "nome",
  data_nascimento: "data_nascimento",
  email: "email",
  senha: "senha",
};

/**
 * Card de autenticação compartilhado pelas telas de login e cadastro.
 * `modoInicial` decide qual aba abre primeiro — Login.jsx e Cadastro.jsx só passam esse prop.
 */
export default function AuthCard({ modoInicial }) {
  const navigate = useNavigate();
  const [modo, setModo] = useState(modoInicial);

  const [loginForm, setLoginForm] = useState({ email: "", senha: "" });
  const [loginErros, setLoginErros] = useState({});
  const [loginBanner, setLoginBanner] = useState("");
  const [loginEnviando, setLoginEnviando] = useState(false);

  const [cadastroForm, setCadastroForm] = useState({ nome: "", data_nascimento: "", email: "", senha: "" });
  const [cadastroErros, setCadastroErros] = useState({});
  const [cadastroBanner, setCadastroBanner] = useState({ texto: "", tipo: "erro" });
  const [cadastroEnviando, setCadastroEnviando] = useState(false);

  function irPara(novoModo) {
    setModo(novoModo);
    navigate(novoModo === "cadastro" ? "/cadastro" : "/login", { replace: false });
  }

  async function aoEnviarLogin(evento) {
    evento.preventDefault();
    setLoginBanner("");
    const erros = {};
    if (!loginForm.email || !REGEX_EMAIL.test(loginForm.email)) erros.email = "Informe um e-mail válido.";
    if (!loginForm.senha) erros.senha = "Informe sua senha.";
    setLoginErros(erros);
    if (Object.keys(erros).length > 0) return;

    setLoginEnviando(true);
    try {
      const resposta = await loginApi({ email: loginForm.email.trim(), senha: loginForm.senha });
      salvarSessao(criarSessao(resposta));
      navigate("/painel");
    } catch (erro) {
      setLoginBanner(erro instanceof ApiError ? erro.message : "Falha de conexão com o servidor. Tente novamente.");
    } finally {
      setLoginEnviando(false);
    }
  }

  async function aoEnviarCadastro(evento) {
    evento.preventDefault();
    setCadastroBanner({ texto: "", tipo: "erro" });
    const erros = {};
    if (!cadastroForm.nome.trim()) erros.nome = "Informe seu nome completo.";
    if (!cadastroForm.data_nascimento) erros.data_nascimento = "Informe sua data de nascimento.";
    if (!cadastroForm.email || !REGEX_EMAIL.test(cadastroForm.email)) erros.email = "Informe um e-mail válido.";
    if (!cadastroForm.senha) erros.senha = "Informe uma senha.";
    setCadastroErros(erros);
    if (Object.keys(erros).length > 0) return;

    setCadastroEnviando(true);
    try {
      await cadastrarUsuario({
        nome: cadastroForm.nome.trim(),
        data_nascimento: cadastroForm.data_nascimento,
        email: cadastroForm.email.trim(),
        senha: cadastroForm.senha,
      });
      setCadastroBanner({
        texto: "Cadastro realizado! Enviamos um e-mail de confirmação. Redirecionando para o login...",
        tipo: "sucesso",
      });
      setTimeout(() => irPara("login"), 1800);
    } catch (erro) {
      if (erro instanceof ApiError && erro.status === 409) {
        setCadastroErros({ email: erro.message });
      } else if (erro instanceof ApiError && erro.status === 422 && Array.isArray(erro.body?.detail)) {
        const novosErros = {};
        let mensagemGeral = "";
        erro.body.detail.forEach((item) => {
          const campo = CAMPO_POR_LOC[item.loc[item.loc.length - 1]];
          const mensagem = item.msg.replace(/^Value error, /, "");
          if (campo) novosErros[campo] = mensagem;
          else mensagemGeral = mensagem;
        });
        setCadastroErros(novosErros);
        if (mensagemGeral) setCadastroBanner({ texto: mensagemGeral, tipo: "erro" });
      } else {
        setCadastroBanner({
          texto: erro instanceof ApiError ? erro.message : "Falha de conexão com o servidor. Tente novamente.",
          tipo: "erro",
        });
      }
    } finally {
      setCadastroEnviando(false);
    }
  }

  const ehCadastro = modo === "cadastro";

  return (
    <div className="auth-page">
      <div className="auth-shell">
        <div className="auth-left">
          <div>
            <div className="auth-kicker">{ehCadastro ? "CRIAR CONTA" : "LOGIN"}</div>
            <Link to="/" className="auth-logo">
              currículo<span>IA</span>
            </Link>
          </div>
          <div className="auth-left-mid">
            <h1 className="auth-title">Seu currículo, otimizado para a vaga certa.</h1>
            <p className="auth-subtitle">Análise inteligente e reestruturação personalizada.</p>
          </div>
          <div className="auth-benefits">
            <div className="benefit-pill"><i className="ti ti-search"></i> Análise com IA em segundos</div>
            <div className="benefit-pill"><i className="ti ti-map-pin"></i> Adequado à vaga específica</div>
            <div className="benefit-pill"><i className="ti ti-settings"></i> Só reescreve, nunca inventa</div>
            <div className="benefit-pill"><i className="ti ti-history"></i> Histórico de análise salva</div>
          </div>
        </div>

        <div className="auth-right">
          <div className="auth-card">
            <div className="auth-tabs">
              <button
                type="button"
                className={`auth-tab ${!ehCadastro ? "active" : ""}`}
                onClick={() => irPara("login")}
              >
                Entrar
              </button>
              <button
                type="button"
                className={`auth-tab ${ehCadastro ? "active" : ""}`}
                onClick={() => irPara("cadastro")}
              >
                Criar conta
              </button>
            </div>

            {!ehCadastro && (
              <>
                {loginBanner && <div className="alert-box erro show">{loginBanner}</div>}
                <form className="auth-form" noValidate onSubmit={aoEnviarLogin}>
                  <div className="field">
                    <label htmlFor="login-email">E-mail</label>
                    <input
                      type="email"
                      id="login-email"
                      placeholder="seu@email.com"
                      value={loginForm.email}
                      onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                    />
                    <span className="field-error">{loginErros.email}</span>
                  </div>
                  <div className="field">
                    <label htmlFor="login-senha">Senha</label>
                    <div className="password-wrap">
                      <input
                        type="password"
                        id="login-senha"
                        placeholder="••••••••"
                        value={loginForm.senha}
                        onChange={(e) => setLoginForm({ ...loginForm, senha: e.target.value })}
                      />
                    </div>
                    <span className="field-error">{loginErros.senha}</span>
                  </div>
                  <p className="auth-switch" style={{ marginTop: "-8px", textAlign: "right" }}>
                    <Link to="/usuarios/recuperar-senha">Esqueceu sua senha?</Link>
                  </p>
                  <button type="submit" className="btn-primary" disabled={loginEnviando}>
                    Entrar
                  </button>
                </form>
                <p className="auth-switch">
                  Não possui conta?{" "}
                  <a href="#" onClick={(e) => { e.preventDefault(); irPara("cadastro"); }}>
                    Criar conta
                  </a>
                </p>
              </>
            )}

            {ehCadastro && (
              <>
                {cadastroBanner.texto && (
                  <div className={`alert-box show ${cadastroBanner.tipo}`}>{cadastroBanner.texto}</div>
                )}
                <form className="auth-form" noValidate onSubmit={aoEnviarCadastro}>
                  <div className="field">
                    <label htmlFor="cad-nome">Nome completo</label>
                    <input
                      type="text"
                      id="cad-nome"
                      placeholder="João Silva"
                      value={cadastroForm.nome}
                      onChange={(e) => setCadastroForm({ ...cadastroForm, nome: e.target.value })}
                    />
                    <span className="field-error">{cadastroErros.nome}</span>
                  </div>
                  <div className="field">
                    <label htmlFor="cad-data">Data de nascimento</label>
                    <input
                      type="date"
                      id="cad-data"
                      value={cadastroForm.data_nascimento}
                      onChange={(e) => setCadastroForm({ ...cadastroForm, data_nascimento: e.target.value })}
                    />
                    <span className="field-error">{cadastroErros.data_nascimento}</span>
                  </div>
                  <div className="field">
                    <label htmlFor="cad-email">E-mail</label>
                    <input
                      type="email"
                      id="cad-email"
                      placeholder="seu@email.com"
                      value={cadastroForm.email}
                      onChange={(e) => setCadastroForm({ ...cadastroForm, email: e.target.value })}
                    />
                    <span className="field-error">{cadastroErros.email}</span>
                  </div>
                  <div className="field">
                    <label htmlFor="cad-senha">Senha</label>
                    <div className="password-wrap">
                      <input
                        type="password"
                        id="cad-senha"
                        placeholder="Mínimo 8 caracteres, 1 maiúscula, 1 número"
                        value={cadastroForm.senha}
                        onChange={(e) => setCadastroForm({ ...cadastroForm, senha: e.target.value })}
                      />
                    </div>
                    <span className="field-error">{cadastroErros.senha}</span>
                  </div>
                  <button type="submit" className="btn-primary" disabled={cadastroEnviando}>
                    Criar conta
                  </button>
                </form>
                <p className="auth-switch">
                  Já possui conta?{" "}
                  <a href="#" onClick={(e) => { e.preventDefault(); irPara("login"); }}>
                    Entrar
                  </a>
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
