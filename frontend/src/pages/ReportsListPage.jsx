import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

export default function ReportsListPage() {
  const [reports, setReports] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/api/reports")
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load reports (${res.status})`);
        return res.json();
      })
      .then(setReports)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <main className="main-grid">
      <motion.div
        className="panel"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <span className="eyebrow">History</span>
        <h3>Past analyses</h3>

        {error && <p className="error-text">{error}</p>}
        {!error && reports === null && <p className="muted">Loading…</p>}
        {reports && reports.length === 0 && (
          <p className="muted">
            No reports yet — run an analysis from the Analyze tab to see it here.
          </p>
        )}

        {reports && reports.length > 0 && (
          <ul className="report-list">
            {reports.map((r) => {
              const highCount = (r.conflicts || []).filter((c) => c.severity === "high").length;
              const id = r.script_id || (r.script_ids && r.script_ids[0]);
              return (
                <li key={id} className="report-list-item">
                  <Link to={`/reports/${encodeURIComponent(id)}`} className="report-list-link">
                    <span className="report-list-title">{id}</span>
                    <span className="report-list-stats">
                      {r.scenes_analyzed} scenes · {(r.conflicts || []).length} conflicts
                      {highCount > 0 && ` · ${highCount} high severity`} ·{" "}
                      {(r.clearance_flags || []).length} legal flags
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </motion.div>
    </main>
  );
}