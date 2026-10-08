import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Cadastro from "./pages/Cadastro.jsx";
import RecuperarSenha from "./pages/RecuperarSenha.jsx";
import RedefinirSenha from "./pages/RedefinirSenha.jsx";
import NovaVaga from "./pages/NovaVaga.jsx";
import UploadCurriculo from "./pages/UploadCurriculo.jsx";
import NovaAnalise from "./pages/NovaAnalise.jsx";
import HistoricoAnalises from "./pages/HistoricoAnalises.jsx";
import GaleriaTemplates from "./pages/GaleriaTemplates.jsx";
import PreviewExportarCurriculo from "./pages/PreviewExportarCurriculo.jsx";
import ChatBot from "./pages/ChatBot.jsx";
import SimulacaoEntrevista from "./pages/SimulacaoEntrevista.jsx";
import VisualizarAnalise from "./pages/VisualizarAnalise.jsx";
import BibliotecaCurriculos from "./pages/BibliotecaCurriculos.jsx";
import ConfiguracoesUsuario from "./pages/ConfiguracoesUsuario.jsx";
import { lerSessao } from "./models/usuario.js";

function RotasAutenticadas() {
  const location = useLocation();
  if (!lerSessao()?.accessToken) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/cadastro" element={<Cadastro />} />
      <Route path="/usuarios/recuperar-senha" element={<RecuperarSenha />} />
      <Route path="/usuarios/redefinir-senha" element={<RedefinirSenha />} />
      <Route element={<RotasAutenticadas />}>
        <Route path="/usuarios/configuracoes" element={<ConfiguracoesUsuario />} />
        <Route path="/analises/nova" element={<NovaAnalise />} />
        <Route path="/analises/historico" element={<HistoricoAnalises />} />
        <Route path="/analises/historico/visualizar" element={<VisualizarAnalise />} />
        <Route path="/analises/biblioteca" element={<BibliotecaCurriculos />} />
        <Route path="/analises/vagas/nova" element={<NovaVaga />} />
        <Route path="/analises/upload" element={<UploadCurriculo />} />
        <Route path="/analises/chat" element={<ChatBot />} />
        <Route path="/templates" element={<GaleriaTemplates />} />
        <Route path="/templates/exportar" element={<PreviewExportarCurriculo />} />
        <Route path="/analises/simulacao" element={<SimulacaoEntrevista />} />
      </Route>
    </Routes>
  );
}
