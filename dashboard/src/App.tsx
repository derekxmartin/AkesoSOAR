import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import { AuthProvider } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Placeholder from "./pages/Placeholder";
import UseCaseDetail from "./pages/UseCaseDetail";
import UseCaseEditor from "./pages/UseCaseEditor";
import UseCases from "./pages/UseCases";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 },
  },
});

export default function App() {
  return (
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
              <Route path="playbooks" element={<Placeholder title="Playbooks" />} />
              <Route path="playbooks/:id" element={<Placeholder title="Playbook Detail" />} />
              <Route path="executions" element={<Placeholder title="Executions" />} />
              <Route path="executions/:id" element={<Placeholder title="Execution Detail" />} />
              <Route path="alerts" element={<Placeholder title="Alerts" />} />
              <Route path="coverage" element={<Placeholder title="MITRE Coverage" />} />
              <Route path="connectors" element={<Placeholder title="Connectors" />} />
              <Route path="audit-log" element={<Placeholder title="Audit Log" />} />
              <Route path="settings" element={<Placeholder title="Settings" />} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
