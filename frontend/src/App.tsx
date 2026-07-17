import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import Login from "./pages/Login";
import { useAuthStore } from "./store/authStore";

function RequireAuth({ children }: { children: JSX.Element }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  return accessToken ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <div className="p-8">Dashboard coming in Task 26</div>
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
