// KubeGraph mark: footholds converging through one hub (the choke point)
// up to the crown-jewel target — the project's thesis, drawn.
// Reads on both light and dark backgrounds.
export default function Logo({ size = 30, title = "KubeGraph" }: { size?: number; title?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none"
         role="img" aria-label={title} xmlns="http://www.w3.org/2000/svg">
      <g strokeLinecap="round">
        <path d="M7 33.5 L20 20" stroke="#64748B" strokeWidth="2" />
        <path d="M20 33.5 L20 20" stroke="#64748B" strokeWidth="2" />
        <path d="M33 33.5 L20 20" stroke="#64748B" strokeWidth="2" />
        <path d="M20 20 L20 7.5" stroke="#F43F5E" strokeWidth="2.6" />
      </g>
      <circle cx="20" cy="7" r="6.6" stroke="#F43F5E" strokeWidth="1.4" opacity="0.3" />
      <circle cx="20" cy="7" r="3.6" fill="#F43F5E" />
      <circle cx="20" cy="20" r="4.3" fill="#6366F1" />
      <circle cx="7" cy="34" r="3.2" fill="#10B981" />
      <circle cx="20" cy="34" r="3.2" fill="#10B981" />
      <circle cx="33" cy="34" r="3.2" fill="#10B981" />
    </svg>
  );
}
