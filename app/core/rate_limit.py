"""
Limitador de requisições (rate limiting) compartilhado pela API.

Fica em módulo próprio (em vez de dentro de main.py) para evitar import circular:
os routers precisam decorar suas rotas com `@limiter.limit(...)`, e main.py precisa
registrar o mesmo `limiter` no app — ambos importam daqui.

Usa armazenamento em memória (padrão do slowapi), suficiente para a única instância
gratuita do Render em que a API roda hoje. Se o serviço crescer para múltiplas
instâncias, isso precisa migrar para um backend compartilhado (Redis) — do contrário
cada instância teria sua própria contagem e o limite real seria N vezes o configurado.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
