export default function FeedbackCarregamento({ mensagem, detalhe, className = "" }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={`feedback-carregamento ${className}`.trim()}
    >
      <div className="feedback-carregamento__documento" aria-hidden="true">
        <i className="ti ti-file-text feedback-carregamento__icone"></i>
        <span className="feedback-carregamento__linha feedback-carregamento__linha--longa"></span>
        <span className="feedback-carregamento__linha"></span>
        <span className="feedback-carregamento__linha feedback-carregamento__linha--curta"></span>
        <span className="feedback-carregamento__scanner"></span>
      </div>
      <div className="feedback-carregamento__texto">
        <p>{mensagem}</p>
        {detalhe && <span>{detalhe}</span>}
      </div>
    </div>
  );
}
