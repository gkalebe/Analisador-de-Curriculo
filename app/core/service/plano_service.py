import re
from collections import Counter

from sqlalchemy.orm import Session

from app.core.persistencia.analise_repository import AnaliseRepository


class PlanoService:
    def __init__(self, db: Session):
        self.analise_repository = AnaliseRepository(db)

    def obter_historico_e_lacunas(self, id_usuario) -> dict:
        analises = self.analise_repository.listar_por_usuario(id_usuario)

        historico = [
            {
                "id_analise": analise.id_analise,
                "data_analise": analise.data_analise,
                "vaga_titulo": analise.vaga.titulo or analise.vaga.area or "Vaga sem título",
                "pontuacao": analise.pontuacao,
            }
            for analise in analises
        ]

        contador_lacunas = Counter()
        for analise in analises:
            for competencia in self._competencias_em_lacuna(analise):
                contador_lacunas[competencia] += 1

        lacunas_recorrentes = [
            {"competencia": competencia, "frequencia": frequencia}
            for competencia, frequencia in contador_lacunas.most_common()
        ]

        return {"historico": historico, "lacunas_recorrentes": lacunas_recorrentes}

    def _competencias_em_lacuna(self, analise) -> list[str]:
        requisitos = (analise.vaga.requisitos or "").strip()
        if not requisitos:
            return []

        texto_curriculo = (analise.curriculo.texto_extraido or "").lower()
        competencias = [item.strip() for item in re.split(r"[,;\n]", requisitos) if item.strip()]
        return [competencia for competencia in competencias if competencia.lower() not in texto_curriculo]
