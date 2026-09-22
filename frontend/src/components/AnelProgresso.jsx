const FAIXAS = [
  { min: 70, cor: "#1e5e3f", rotulo: "Aderência forte" },
  { min: 50, cor: "#d97706", rotulo: "Aderência moderada" },
  { min: 0, cor: "#dc2626", rotulo: "Aderência baixa" },
];

export function classificarAderencia(pontuacao) {
  const p = pontuacao ?? 0;
  return FAIXAS.find((faixa) => p >= faixa.min) || FAIXAS[FAIXAS.length - 1];
}

export default function AnelProgresso({ pontuacao, tamanho = 44, espessura = 4, mostrarTexto = true }) {
  const p = Math.max(0, Math.min(100, pontuacao ?? 0));
  const raio = (tamanho - espessura) / 2;
  const circunferencia = 2 * Math.PI * raio;
  const preenchido = (p / 100) * circunferencia;
  const { cor } = classificarAderencia(p);

  return (
    <div className="relative shrink-0" style={{ width: tamanho, height: tamanho }}>
      <svg width={tamanho} height={tamanho} className="-rotate-90">
        <circle
          cx={tamanho / 2}
          cy={tamanho / 2}
          r={raio}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={espessura}
        />
        <circle
          cx={tamanho / 2}
          cy={tamanho / 2}
          r={raio}
          fill="none"
          stroke={cor}
          strokeWidth={espessura}
          strokeLinecap="round"
          strokeDasharray={circunferencia}
          strokeDashoffset={circunferencia - preenchido}
        />
      </svg>
      {mostrarTexto && (
        <span
          className="absolute inset-0 flex items-center justify-center font-brand font-bold text-black"
          style={{ fontSize: tamanho * 0.26 }}
        >
          {Math.round(p)}%
        </span>
      )}
    </div>
  );
}
