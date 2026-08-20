import { motion, AnimatePresence } from "framer-motion";

const severityLabel = { high: "Contradiction", medium: "State violation", low: "Unresolved thread" };

export function ConflictList({ conflicts, selected, onSelect }) {
  if (conflicts.length === 0) {
    return <EmptyState text="No continuity conflicts detected in this script." />;
  }
  return (
    <div className="panel list-panel">
      <span className="eyebrow">Continuity conflicts</span>
      <ul className="flag-list">
        {conflicts
          .slice()
          .sort((a, b) => severityRank(b.severity) - severityRank(a.severity))
          .map((c) => (
            <li key={c.conflict_id}>
              <button
                className={`flag-row severity-${c.severity} ${selected?.conflict_id === c.conflict_id ? "active" : ""}`}
                onClick={() => onSelect(c)}
              >
                <span className={`badge badge-${c.severity}`}>{severityLabel[c.severity] || c.conflict_type}</span>
                <span className="flag-summary">{c.summary}</span>
                <span className="flag-confidence">{Math.round(c.confidence * 100)}%</span>
              </button>
            </li>
          ))}
      </ul>
    </div>
  );
}

export function ClearanceList({ flags }) {
  if (flags.length === 0) {
    return <EmptyState text="No legal clearance flags in this script." />;
  }
  return (
    <div className="panel list-panel">
      <span className="eyebrow">Legal clearance</span>
      <ul className="flag-list">
        {flags.map((f) => (
          <li key={f.flag_id}>
            <div className="flag-row severity-medium static">
              <span className="badge badge-amber">{f.reference_type}</span>
              <span className="flag-summary">
                “{f.reference_text}” — {f.risk_note}
              </span>
              <span className="flag-confidence">{Math.round(f.confidence * 100)}%</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ConflictDetail({ conflict, onClose }) {
  return (
    <AnimatePresence>
      {conflict && (
        <motion.div
          className="detail-drawer"
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 24 }}
          transition={{ duration: 0.25 }}
        >
          <button className="close-btn" onClick={onClose} aria-label="Close detail">
            ×
          </button>
          <span className={`badge badge-${conflict.severity}`}>
            {severityLabel[conflict.severity] || conflict.conflict_type}
          </span>
          <h3>{conflict.summary}</h3>
          <p className="muted">{conflict.explanation}</p>
          <div className="detail-meta">
            <div>
              <span className="field-label">Source scenes</span>
              <p>{conflict.source_scene_ids.join(" ↔ ")}</p>
            </div>
            <div>
              <span className="field-label">Confidence</span>
              <p>{Math.round(conflict.confidence * 100)}%</p>
            </div>
            <div>
              <span className="field-label">Status</span>
              <p>{conflict.requires_human_review ? "Requires human review" : "Auto-resolved"}</p>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function EmptyState({ text }) {
  return (
    <div className="panel empty-state">
      <p className="muted">{text}</p>
    </div>
  );
}

function severityRank(s) {
  return { high: 3, medium: 2, low: 1 }[s] || 0;
}
