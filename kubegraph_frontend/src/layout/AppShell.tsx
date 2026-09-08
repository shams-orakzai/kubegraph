import { createContext, useContext, useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { ClusterProvider } from "../cluster/ClusterContext";
import { useAuth } from "../auth/AuthContext";

export type Role = "engineer" | "platform" | "ciso";

interface RoleControl { role: Role; setRole: (r: Role) => void; }
const RoleCtx = createContext<RoleControl>({ role: "engineer", setRole: () => {} });

// Backwards-compatible: existing callers use useRole() to read the value.
export const useRole = () => useContext(RoleCtx).role;
// Settings uses this to change the active persona.
export const useRoleControl = () => useContext(RoleCtx);

const ROLE_KEY = "kg_role";

export default function AppShell() {
  const { user } = useAuth();
  const initial = (localStorage.getItem(ROLE_KEY) as Role) || (user?.role as Role) || "engineer";
  const [role, setRoleState] = useState<Role>(initial);

  const setRole = (r: Role) => {
    setRoleState(r);
    localStorage.setItem(ROLE_KEY, r); // persona persists across reloads
  };

  return (
    <ClusterProvider>
      <RoleCtx.Provider value={{ role, setRole }}>
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
