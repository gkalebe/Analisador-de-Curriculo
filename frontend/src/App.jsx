import { Routes, Route } from "react-router-dom";
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
import EditarCurriculo from "./pages/EditarCurriculo.jsx";
import ChatBot from "./pages/ChatBot.jsx";
import SimulacaoEntrevista from "./pages/SimulacaoEntrevista.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/cadastro" element={<Cadastro />} />
      <Route path="/usuarios/recuperar-senha" element={<RecuperarSenha />} />
      <Route path="/usuarios/redefinir-senha" element={<RedefinirSenha />} />
      <Route path="/analises/nova" element={<NovaAnalise />} />
      <Route path="/analises/historico" element={<HistoricoAnalises />} />
      <Route path="/analises/vagas/nova" element={<NovaVaga />} />
      <Route path="/analises/upload" element={<UploadCurriculo />} />
      <Route path="/analises/chat" element={<ChatBot />} />
      <Route path="/templates" element={<GaleriaTemplates />} />
      <Route path="/templates/exportar" element={<PreviewExportarCurriculo />} />
      <Route path="/analises/editar" element={<EditarCurriculo />} />
      <Route path="/analises/simulacao" element={<SimulacaoEntrevista />} />
    </Routes>
  );
}
