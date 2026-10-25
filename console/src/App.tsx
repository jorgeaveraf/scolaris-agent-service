import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./providers/AuthProvider";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { AdminOnlyRoute } from "./routes/AdminOnlyRoute";
import { LoginPage } from "./pages/LoginPage";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { DocumentChunksPage } from "./pages/DocumentChunksPage";
import { ObservabilityPage } from "./pages/ObservabilityPage";
import { UsersPage } from "./pages/UsersPage";
import { ChatHistoryPage } from "./pages/ChatHistoryPage";
import { LanguageProvider } from "./i18n/LanguageProvider";
import { AccentProvider } from "./theme/AccentProvider";

export default function App() {
  return (
    <LanguageProvider><AccentProvider><AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<DashboardLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="documents/:id" element={<DocumentChunksPage />} />
              <Route path="observability" element={<ObservabilityPage />} />
              <Route path="chunks" element={<Navigate to="/documents" replace />} />
              <Route path="logs" element={<Navigate to="/observability" replace />} />
              <Route element={<AdminOnlyRoute />}>
                <Route path="users" element={<UsersPage />} />
                <Route path="chat-history" element={<ChatHistoryPage />} />
              </Route>
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
      </BrowserRouter>
    </AuthProvider></AccentProvider></LanguageProvider>
  );
}
