import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import Dashboard from "./pages/Dashboard";
import ExecutionView from "./pages/ExecutionView";
import Executions from "./pages/Executions";
import Login from "./pages/Login";
import Placeholder from "./pages/Placeholder";
import PlaybookDetail from "./pages/PlaybookDetail";
import PlaybookEditPage from "./pages/PlaybookEditPage";
import Playbooks from "./pages/Playbooks";
import UseCaseDetail from "./pages/UseCaseDetail";
import UseCaseEditor from "./pages/UseCaseEditor";
import MitreCoverage from "./pages/MitreCoverage";
import UseCaseBoard from "./pages/UseCaseBoard";
import UseCases from "./pages/UseCases";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 },
  },
});

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route element={<AppShell />}>
                <Route index element={<Dashboard />} />
                <Route path="use-cases" element={<UseCases />} />
                <Route path="use-cases/new" element={<UseCaseEditor />} />
                <Route path="use-cases/:id" element={<UseCaseDetail />} />
                <Route path="use-cases/:id/edit" element={<UseCaseEditor />} />
                <Route path="playbooks" element={<Playbooks />} />
                <Route path="playbooks/new" element={<PlaybookEditPage />} />
                <Route path="playbooks/:id" element={<PlaybookDetail />} />
                <Route path="playbooks/:id/edit" element={<PlaybookEditPage />} />
                <Route path="executions" element={<Executions />} />
                <Route path="executions/:id" element={<ExecutionView />} />
                <Route path="alerts" element={<Placeholder title="Alerts" />} />
                <Route path="use-cases/board" element={<UseCaseBoard />} />
                <Route path="coverage" element={<MitreCoverage />} />
                <Route path="connectors" element={<Placeholder title="Connectors" />} />
                <Route path="audit-log" element={<Placeholder title="Audit Log" />} />
                <Route path="settings" element={<Placeholder title="Settings" />} />
              </Route>
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
