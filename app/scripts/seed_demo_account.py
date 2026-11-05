import sys
from datetime import date

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.persistencia.models.usuario import Usuario
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.auth_service import pwd_context


def main() -> int:
    settings = get_settings()
    if settings.environment.lower() not in {"development", "dev", "test", "local"}:
        raise RuntimeError("A conta de demonstração só pode ser criada em desenvolvimento ou teste.")
    if not settings.demo_account_email or not settings.demo_account_password:
        raise RuntimeError("Configure DEMO_ACCOUNT_EMAIL e DEMO_ACCOUNT_PASSWORD no .env local.")
    if len(settings.demo_account_password) < 12:
        raise RuntimeError("DEMO_ACCOUNT_PASSWORD precisa ter pelo menos 12 caracteres.")

    db = SessionLocal()
    try:
        repository = UsuarioRepository(db)
        usuario = repository.buscar_por_email(settings.demo_account_email.strip().lower())
        if usuario is None:
            usuario = Usuario(
                nome="Conta Demo",
                data_nascimento=date(2000, 1, 1),
                email=settings.demo_account_email.strip().lower(),
                senha_hash=pwd_context.hash(settings.demo_account_password),
                plano_codigo="ultimate",
            )
            repository.criar(usuario)
        else:
            usuario.senha_hash = pwd_context.hash(settings.demo_account_password)
            usuario.plano_codigo = "ultimate"
            repository.atualizar(usuario)
        print(f"Conta Ultimate de demonstração pronta: {usuario.email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        raise SystemExit(1) from erro
