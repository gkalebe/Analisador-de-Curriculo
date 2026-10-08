import { requisitar } from "./client";
import { lerSessao } from "../models/usuario.js";

export function cadastrarUsuario({ nome, data_nascimento, email, senha }) {
  return requisitar("/usuarios", {
    method: "POST",
    body: { nome, data_nascimento, email, senha },
  });
}

export function login({ email, senha }) {
  return requisitar("/usuarios/login", {
    method: "POST",
    body: { email, senha },
  });
}

export function solicitarRecuperacaoSenha(email) {
  return requisitar("/usuarios/recuperar-senha", {
    method: "POST",
    body: { email },
  });
}

export function redefinirSenha({ token, nova_senha }) {
  return requisitar("/usuarios/redefinir-senha", {
    method: "POST",
    body: { token, nova_senha },
  });
}

export function obterPerfilUsuario() {
  return requisitar("/usuarios/me", {
    token: lerSessao()?.accessToken,
  });
}

export function atualizarPerfilUsuario({ nome, notificacoes_por_email }) {
  return requisitar("/usuarios/me", {
    method: "PATCH",
    body: { nome, notificacoes_por_email },
    token: lerSessao()?.accessToken,
  });
}

export function obterStatusExclusaoConta() {
  return requisitar("/usuarios/exclusao", {
    token: lerSessao()?.accessToken,
  });
}

export function solicitarExclusaoConta() {
  return requisitar("/usuarios/exclusao", {
    method: "POST",
    token: lerSessao()?.accessToken,
  });
}

export function cancelarExclusaoConta() {
  return requisitar("/usuarios/exclusao/cancelar", {
    method: "POST",
    token: lerSessao()?.accessToken,
  });
}

export function confirmarExclusaoConta() {
  return requisitar("/usuarios/exclusao/confirmar", {
    method: "POST",
    token: lerSessao()?.accessToken,
  });
}
