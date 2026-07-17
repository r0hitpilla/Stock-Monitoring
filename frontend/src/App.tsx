import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Link, Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Login from "./pages/Login";
import Logs from "./pages/Logs";
import Notifications from "./pages/Notifications";
import Products from "./pages/Products";
import Retailers from "./pages/Retailers";
import Settings from "./pages/Settings";
import { useAuthStore } from "./store/authStore";

const queryClient = new QueryClient();

function RequireAuth({ children }: { children: JSX.Element }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  return accessToken ? children : <Navigate to="/login" replace />;
}

function Nav() {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (!accessToken) return null;
  const links: [string, string][] = [
    ["/", "Dashboard"],
    ["/products", "Products"],
    ["/retailers", "Retailers"],
    ["/history", "History"],
    ["/notifications", "Notifications"],
    ["/logs", "Logs"],
    ["/settings", "Settings"],
  ];
  return (
    <nav className="flex gap-4 border-b border-white/10 p-4 text-sm">
      {links.map(([to, label]) => (
        <Link key={to} to={to}>{label}</Link>
      ))}
    </nav>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Nav />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            }
          />
          <Route
            path="/products"
            element={
              <RequireAuth>
                <Products />
              </RequireAuth>
            }
          />
          <Route
            path="/retailers"
            element={
              <RequireAuth>
                <Retailers />
              </RequireAuth>
            }
          />
          <Route
            path="/history"
            element={
              <RequireAuth>
                <History />
              </RequireAuth>
            }
          />
          <Route
            path="/notifications"
            element={
              <RequireAuth>
                <Notifications />
              </RequireAuth>
            }
          />
          <Route
            path="/logs"
            element={
              <RequireAuth>
                <Logs />
              </RequireAuth>
            }
          />
          <Route
            path="/settings"
            element={
              <RequireAuth>
                <Settings />
              </RequireAuth>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
