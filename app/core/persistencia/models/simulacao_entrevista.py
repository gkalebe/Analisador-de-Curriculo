import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .usuario import Usuario
    from .vaga import Vaga

DIMENSOES_FEEDBACK = ("clareza", "objetividade", "coerencia", "alinhamento")


def calcular_nota_final(perguntas: list[dict]) -> float | None:
    """Média (0-10, uma casa decimal) de todas as notas das 4 dimensões em todas as perguntas
    que têm feedback. Usada na avaliação em lote e, na leitura, nas simulações antigas
    (avaliadas pergunta a pergunta), que não têm `nota_final` gravada."""
    notas = []
    for pergunta in perguntas or []:
        feedback = pergunta.get("feedback") or {}
        for dimensao in DIMENSOES_FEEDBACK:
            nota = (feedback.get(dimensao) or {}).get("nota")
            if isinstance(nota, (int, float)) and not isinstance(nota, bool):
                notas.append(float(nota))
    if not notas:
        return None
    return round(sum(notas) / len(notas), 1)


class SimulacaoEntrevista(Base):
    __tablename__ = "simulacao_entrevista"

    id_simulacao: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)
    id_vaga: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vaga.id_vaga", ondelete="CASCADE"), nullable=False
    )
    # Cada item: {id_pergunta, tipo (comportamental/tecnica/situacional), texto, resposta,
    # feedback: {clareza, objetividade, coerencia, alinhamento (cada um {nota, comentario}),
    # feedback_geral} ou None, respondida_em}.
    # Guardado como JSON (mesmo padrão de curriculo.dados_editados) por ser um agregado que só
    # faz sentido lido/gravado por inteiro junto da simulação — não precisa de tabela própria.
    perguntas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Avaliação em lote (uma única chamada de IA para todas as respostas). `avaliada_em` nulo =
    # simulação pendente de respostas (ou antiga, avaliada pergunta a pergunta — ver `legada`).
    avaliada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nota_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_geral: Mapped[str | None] = mapped_column(Text, nullable=True)

    usuario: Mapped["Usuario"] = relationship(back_populates="simulacoes_entrevista")
    vaga: Mapped["Vaga"] = relationship(back_populates="simulacoes_entrevista")

    @property
    def legada(self) -> bool:
        """Simulação do fluxo antigo (feedback por pergunta): fica somente leitura."""
        return self.avaliada_em is None and any(p.get("feedback") for p in (self.perguntas or []))

    @property
    def status(self) -> str:
        return "avaliada" if self.avaliada_em is not None or self.legada else "pendente"

    @property
    def nota_geral(self) -> float | None:
        if self.nota_final is not None:
            return self.nota_final
        return calcular_nota_final(self.perguntas) if self.legada else None

    @property
    def vaga_titulo(self) -> str | None:
        vaga = self.vaga
        if vaga is None:
            return None
        return vaga.titulo or vaga.area or None

    @property
    def total_perguntas(self) -> int:
        return len(self.perguntas or [])

    @property
    def total_respondidas(self) -> int:
        return len([p for p in (self.perguntas or []) if p.get("resposta")])
