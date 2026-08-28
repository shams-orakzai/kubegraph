import { createContext, useContext, useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { ClusterProvider } from "../cluster/ClusterContext";
import { useAuth } from "../auth/AuthContext";

export type Role = "engineer" | "platform" | "ciso";
const RoleCtx = createContext<Role>("engineer");
export const useRole = () => useContext(RoleCtx);

export default function AppShell() {
  const { user } = useAuth();
  const [role, setRole] = useState<Role>((user?.role as Role) || "engineer");

  return (
    <ClusterProvider>
      <RoleCtx.Provider value={role}>
        <div className="shell">
          <Sidebar />
          <div className="main">
            <TopBar role={role} onRole={setRole} />
            <div className="viewport">
              <Outlet />
            </div>
          </div>
        </div>
      </RoleCtx.Provider>
    </ClusterProvider>
  );
}
