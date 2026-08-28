const BAND_COLOR: Record<string, string> = {
  Low: "var(--low)", Medium: "var(--med)", High: "var(--high)",
};

const R = 54;
const C = 2 * Math.PI * R;

export default function ExposureDonut({ score, band }: { score: number; band: string }) {
  const offset = C * (1 - Math.max(0, Math.min(100, score)) / 100);
  const color = BAND_COLOR[band] || "var(--med)";
  return (
    <div className="ring">
      <svg width="128" height="128" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={R} fill="none" stroke="#EEF2F7" strokeWidth="12" />
        <circle cx="64" cy="64" r={R} fill="none" stroke={color} strokeWidth="12"
                strokeLinecap="round" strokeDasharray={C} strokeDashoffset={offset} />
      </svg>
      <div className="c"><b style={{ color }}>{score}</b><small>{band}</small></div>
    </div>
  );
}
