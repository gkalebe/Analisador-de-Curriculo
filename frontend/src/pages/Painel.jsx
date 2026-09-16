import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { lerSessao, limparSessao } from "../models/usuario.js";

export default function Painel() {
  const navigate = useNavigate();
  const [sessao, setSessao] = useState(null);

  useEffect(() => {
    const atual = lerSessao();
    if (!atual) {
      navigate("/login");
      return;
    }
    setSessao(atual);
  }, [navigate]);

  function sair() {
    limparSessao();
    navigate("/login");
  }

  if (!sessao) return null;

  const linkNovaAnalise = `/analises/nova?email=${encodeURIComponent(sessao.email)}`;
  const linkNovaVaga = `/analises/vagas/nova?email=${encodeURIComponent(sessao.email)}`;
  const linkUpload = `/analises/upload?email=${encodeURIComponent(sessao.email)}`;
  const linkTemplates = `/templates?email=${encodeURIComponent(sessao.email)}`;

  return (
    <div className="placeholder-wrap">
      <div className="placeholder-card">
        <h1>Bem-vindo(a), {sessao.nome || "—"}</h1>
        <p>
          Este é o painel principal. As funcionalidades completas do painel (histórico e evolução das análises)
          são da US-016, ainda não implementada — esta tela existe para validar o redirecionamento pós-login da
          US-002.
        </p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link className="btn-primary" to={linkNovaAnalise}>
            Nova análise
          </Link>
          <Link className="btn-primary" to={linkNovaVaga}>
            Cadastrar vaga
          </Link>
          <Link className="btn-primary" to={linkUpload}>
            Enviar currículo
          </Link>
          <Link className="btn-primary" to={linkTemplates}>
            Templates ATS
          </Link>
          <button className="btn-secondary" onClick={sair}>
            Sair
          </button>
        </div>
      </div>
    </div>
  );
}
