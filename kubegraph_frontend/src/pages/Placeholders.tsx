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

export function Settings() {
  return <Placeholder badge="LATER" title="Settings"
    note="Workspace, cluster connections, and team management." />;
}
