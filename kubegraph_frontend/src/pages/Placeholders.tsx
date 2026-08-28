function Placeholder({ badge, title, note }: { badge: string; title: string; note: string }) {
  return (
    <div className="page">
      <div className="placeholder">
        <div>
          <span className="badge">{badge}</span>
          <h2>{title}</h2>
          <p>{note}</p>
        </div>
      </div>
    </div>
  );
}

export function Remediations() {
  return <Placeholder badge="INCREMENT 5" title="Remediations"
    note="Ranked choke-point fixes with preview and impact." />;
}
export function Fleet() {
  return <Placeholder badge="INCREMENT 5" title="Fleet"
    note="Compare exposure across every connected cluster." />;
}
export function Settings() {
  return <Placeholder badge="LATER" title="Settings"
    note="Workspace, cluster connections, and team management." />;
}
