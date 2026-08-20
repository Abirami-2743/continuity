import { motion } from "framer-motion";

export default function ReportSummary({ report, onNarrate, narrating }) {
  const highCount = report.conflicts.filter((c) => c.severity === "high").length;

  const stats = [
    { label: "Scenes analyzed", value: report.scenes_analyzed },
    { label: "Facts extracted", value: report.facts_extracted },
    { label: "Conflicts found", value: report.conflicts.length },
    { label: "High severity", value: highCount },
    { label: "Legal flags", value: report.clearance_flags.length },
  ];

  return (
    <motion.div
      className="panel summary-panel"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="summary-stats">
        {stats.map((s) => (
          <div key={s.label} className="stat">
            <span className="stat-value">{s.value}</span>
            <span className="stat-label">{s.label}</span>
          </div>
        ))}
      </div>
      <div className="summary-text-row">
        <p className="summary-text">{report.summary_text}</p>
        <button className="btn-secondary narrate-btn" onClick={onNarrate} disabled={narrating}>
          {narrating ? "Generating audio…" : "🔊 Listen to summary"}
        </button>
      </div>
    </motion.div>
  );
}
