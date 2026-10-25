import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function AdminOnlyRoute() {
  const { role } = useAuth();
  return role === "admin" ? <Outlet /> : <Navigate to="/dashboard" replace />;
}
