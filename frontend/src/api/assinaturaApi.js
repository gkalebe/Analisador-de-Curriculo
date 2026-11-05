import { requisitar } from "./client.js";
import { lerSessao } from "../models/usuario.js";

export function obterPlanos() {
  return requisitar("/assinaturas/planos");
}

export function obterUsoPlano() {
  return requisitar("/assinaturas/me/uso", {
    token: lerSessao()?.accessToken,
  });
}

export function criarCheckout(planoCodigo) {
  return requisitar("/assinaturas/checkout", {
    method: "POST",
    body: { plano_codigo: planoCodigo },
  });
}

export function alterarPlano(planoCodigo) {
  return requisitar("/assinaturas/alterar-plano", {
    method: "POST",
    body: { plano_codigo: planoCodigo },
  });
}

export function abrirPortalAssinatura() {
  return requisitar("/assinaturas/portal", { method: "POST" });
}

export function cancelarRenovacao() {
  return requisitar("/assinaturas/cancelar", { method: "POST" });
}
