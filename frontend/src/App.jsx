import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Cadastro from "./pages/Cadastro.jsx";
import Painel from "./pages/Painel.jsx";
import RecuperarSenha from "./pages/RecuperarSenha.jsx";
import RedefinirSenha from "./pages/RedefinirSenha.jsx";
import NovaVaga from "./pages/NovaVaga.jsx";
import UploadCurriculo from "./pages/UploadCurriculo.jsx";
import NovaAnalise from "./pages/NovaAnalise.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/cadastro" element={<Cadastro />} />
      <Route path="/painel" element={<Painel />} />
      <Route path="/usuarios/recuperar-senha" element={<RecuperarSenha />} />
      <Route path="/usuarios/redefinir-senha" element={<RedefinirSenha />} />
      <Route path="/analises/nova" element={<NovaAnalise />} />
      <Route path="/analises/vagas/nova" element={<NovaVaga />} />
      <Route path="/analises/upload" element={<UploadCurriculo />} />
    </Routes>
  );
}
