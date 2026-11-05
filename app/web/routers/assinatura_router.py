import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.adapters.stripe.stripe_adapter import StripeConfiguracaoInvalidaError
from app.core.database import get_db
from app.core.persistencia.assinatura_repository import AssinaturaRepository
from app.core.service.catalogo_planos import PLANOS
from app.core.service.assinatura_service import (
    AssinaturaInvalidaError,
    AssinaturaService,
    StripeEventoEmProcessamentoError,
)
from app.core.service.uso_ia_service import UsoIAService
from app.web.dependencies import get_usuario_atual
from app.web.schemas_assinatura import (
    AlterarPlanoRequest,
    LinkAssinaturaResponse,
    MensagemAssinaturaResponse,
    PlanoCatalogoResponse,
    PlanosCatalogoResponse,
    UsoAtualResponse,
    UsoPlanoResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assinaturas", tags=["Planos e uso"])


def _plano_response(plano) -> PlanoCatalogoResponse:
    return PlanoCatalogoResponse(
        **{
            nome: getattr(plano, nome)
            for nome in PlanoCatalogoResponse.model_fields
            if nome != "creditos_demais_operacoes"
        },
        creditos_demais_operacoes=plano.creditos_demais_operacoes,
    )


@router.get("/planos", response_model=PlanosCatalogoResponse)
def listar_planos() -> PlanosCatalogoResponse:
    return PlanosCatalogoResponse(planos=[_plano_response(plano) for plano in PLANOS.values()])


@router.get("/me/uso", response_model=UsoAtualResponse)
def obter_uso_atual(
    usuario=Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> UsoAtualResponse:
    try:
        servico = AssinaturaService(db)
        checkout_sincronizado = servico.sincronizar_checkout_pendente(usuario)
        if not checkout_sincronizado:
            servico.sincronizar_assinatura_atual(usuario)
    except stripe.StripeError as erro:
        logger.exception("Falha ao sincronizar a assinatura com a Stripe.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível consultar a confirmação do pagamento.",
        ) from erro
    except Exception as erro:
        logger.exception("Falha ao sincronizar o estado da assinatura.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível sincronizar a assinatura.",
        ) from erro

    resumo = UsoIAService(db).obter_resumo(usuario.id_usuario)
    assinatura = AssinaturaRepository(db).buscar_por_usuario(usuario.id_usuario)
    return UsoAtualResponse(
        uso=UsoPlanoResponse(
            plano=_plano_response(resumo["plano"]),
            inicio_janela=resumo["inicio_janela"],
            fim_janela=resumo["fim_janela"],
            usos=resumo["usos"],
            assinatura_status=assinatura.status if assinatura else None,
            plano_pendente_codigo=assinatura.plano_pendente_codigo if assinatura else None,
            cancelamento_agendado=assinatura.cancelamento_agendado if assinatura else False,
            acesso_ate=assinatura.periodo_fim if assinatura else None,
        )
    )


@router.post("/checkout", response_model=LinkAssinaturaResponse)
def criar_checkout(
    payload: AlterarPlanoRequest,
    usuario=Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> LinkAssinaturaResponse:
    try:
        url = AssinaturaService(db).iniciar_checkout(usuario, payload.plano_codigo)
        return LinkAssinaturaResponse(url=url)
    except AssinaturaInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    except StripeConfiguracaoInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except stripe.StripeError as erro:
        logger.exception("Falha ao criar Checkout Stripe.")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Não foi possível iniciar o pagamento.") from erro


@router.post("/portal", response_model=LinkAssinaturaResponse)
def criar_portal(
    usuario=Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> LinkAssinaturaResponse:
    try:
        url = AssinaturaService(db).criar_portal(usuario)
        return LinkAssinaturaResponse(url=url)
    except AssinaturaInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    except StripeConfiguracaoInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except stripe.StripeError as erro:
        logger.exception("Falha ao criar sessão do Customer Portal Stripe.")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Não foi possível abrir o portal.") from erro


@router.post("/alterar-plano", response_model=MensagemAssinaturaResponse)
def alterar_plano(
    payload: AlterarPlanoRequest,
    usuario=Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> MensagemAssinaturaResponse:
    try:
        mensagem = AssinaturaService(db).alterar_plano(usuario, payload.plano_codigo)
        return MensagemAssinaturaResponse(mensagem=mensagem)
    except AssinaturaInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    except StripeConfiguracaoInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except stripe.StripeError as erro:
        logger.exception("Falha ao alterar plano Stripe.")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Não foi possível alterar o plano.") from erro


@router.post("/cancelar", response_model=MensagemAssinaturaResponse)
def cancelar_renovacao(
    usuario=Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> MensagemAssinaturaResponse:
    try:
        AssinaturaService(db).cancelar_renovacao(usuario)
        return MensagemAssinaturaResponse(mensagem="A renovação foi cancelada; seu acesso permanece até o fim do ciclo.")
    except AssinaturaInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    except StripeConfiguracaoInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except stripe.StripeError as erro:
        logger.exception("Falha ao cancelar renovação Stripe.")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Não foi possível cancelar a renovação.") from erro


@router.post("/webhook")
async def receber_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    if not stripe_signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assinatura Stripe ausente.")
    payload = await request.body()
    service = AssinaturaService(db)
    try:
        event = service.stripe.validar_evento(payload, stripe_signature)
    except StripeConfiguracaoInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except (stripe.SignatureVerificationError, ValueError) as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook Stripe inválido.") from erro

    try:
        processado = service.processar_evento(event)
    except StripeEventoEmProcessamentoError as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evento Stripe está sendo processado; tente novamente.",
        ) from erro
    except Exception as erro:
        logger.exception("Falha ao processar evento Stripe.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao processar webhook.") from erro
    return {"recebido": True, "duplicado": not processado}
