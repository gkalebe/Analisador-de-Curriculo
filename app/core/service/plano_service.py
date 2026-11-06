import re
from collections import Counter

from sqlalchemy.orm import Session

from app.core.persistencia.analise_repository import AnaliseRepository
from app.core.service.plano_desenvolvimento import consolidar_planos, montar_plano_desenvolvimento
from app.core.service.recomendacoes_competencias import resultado_analise_como_dict


class PlanoService:
    def __init__(self, db: Session):
        self.analise_repository = AnaliseRepository(db)

    def obter_historico_e_lacunas(self, id_usuario, limit: int | None = None, offset: int = 0) -> dict:
        # As lacunas recorrentes são um agregado sobre TODAS as análises do usuário, então a
        # leitura continua completa; a paginação recorta apenas a lista `historico`.
        analises = self.analise_repository.listar_por_usuario(id_usuario)
        fim = None if limit is None else offset + limit

        historico = [
            {
                "id_analise": analise.id_analise,
                "data_analise": analise.data_analise,
                "vaga_titulo": analise.vaga.titulo or analise.vaga.area or "Vaga sem título",
                "pontuacao": analise.pontuacao,
            }
            for analise in analises[offset:fim]
        ]

        contador_lacunas = Counter()
        for analise in analises:
            for competencia in self._competencias_em_lacuna(analise):
                contador_lacunas[competencia] += 1

        lacunas_recorrentes = [
            {"competencia": competencia, "frequencia": frequencia}
            for competencia, frequencia in contador_lacunas.most_common()
        ]

        return {
            "historico": historico,
            "total_historico": len(analises),
            "lacunas_recorrentes": lacunas_recorrentes,
        }

    def _competencias_em_lacuna(self, analise) -> list[str]:
        requisitos = (analise.vaga.requisitos or "").strip()
        if not requisitos:
            return []

        texto_curriculo = (analise.curriculo.texto_extraido or "").lower()
        competencias = [item.strip() for item in re.split(r"[,;\n]", requisitos) if item.strip()]
        return [competencia for competencia in competencias if competencia.lower() not in texto_curriculo]

    def obter_plano_desenvolvimento(self, id_usuario) -> dict:
        """US-015: dashboard com a trilha de cada requisito não atendido nas vagas analisadas.

        Considera só a análise mais recente de cada vaga, para que uma lacuna já resolvida em uma
        reanálise não continue aparecendo no plano.
        """
        planos = []
        vagas_vistas = set()
        for analise in self.analise_repository.listar_por_usuario(id_usuario):
            if analise.id_vaga in vagas_vistas:
                continue
            vagas_vistas.add(analise.id_vaga)
            referencia = {
                "id_analise": analise.id_analise,
                "vaga_titulo": (analise.vaga.titulo or analise.vaga.area or "Vaga sem título")
                if analise.vaga
                else "Vaga sem título",
            }
            planos.append(
                (referencia, montar_plano_desenvolvimento(resultado_analise_como_dict(analise.observacoes)))
            )
        return consolidar_planos(planos)
