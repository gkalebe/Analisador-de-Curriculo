# Mantido apenas por compatibilidade — os schemas agora ficam separados por domínio
# em schemas_auth.py, schemas_vaga.py, schemas_curriculo.py, schemas_analise.py e
# schemas_template.py. Prefira importar diretamente desses módulos.
from app.web.schemas_analise import AnaliseListResponse, AnaliseResponse  # noqa: F401
from app.web.schemas_auth import (  # noqa: F401
    REGRAS_SENHA,
    CadastrarUsuarioRequest,
    LoginRequest,
    LoginResponse,
    MensagemResponse,
    RedefinirSenhaRequest,
    SolicitarRecuperacaoSenhaRequest,
    UsuarioResponse,
    validar_regras_senha,
)
from app.web.schemas_curriculo import CurriculoResponse  # noqa: F401
from app.web.schemas_template import (  # noqa: F401
    TemplateListResponse,
    TemplatePreviewFicticio,
    TemplateResponse,
)
from app.web.schemas_vaga import (  # noqa: F401
    VagaCreateRequest,
    VagaListResponse,
    VagaResponse,
)
