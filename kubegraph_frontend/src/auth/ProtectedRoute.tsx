import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "./AuthContext";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  if (!ready) {
    return <div className="center-screen"><div className="spinner" /></div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
