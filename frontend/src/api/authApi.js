import { requisitar } from "./client";

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
