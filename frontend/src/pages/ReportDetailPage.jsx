import { useEffect, useState } from "react";
import { useParams, useLocation, Link } from "react-router-dom";
import { motion } from "framer-motion";
import ReportSummary from "../components/ReportSummary.jsx";
import StoryTimeline from "../components/StoryTimeline.jsx";
import { ConflictList, ClearanceList, ConflictDetail } from "../components/ConflictPanels.jsx";

export default function ReportDetailPage() {
  const { scriptId } = useParams();
  const location = useLocation();

  // Coming straight from the analyze flow, the report is already in hand
  // (passed via navigate state) — skip the extra round trip. Coming from a
  // bookmark, refresh, or the reports list, fetch it by id instead.
  const [report, setReport] = useState(location.state?.report ?? null);
  const [loading, setLoading] = useState(!location.state?.report);
  const [error, setError] = useState(null);
  const [selectedConflict, setSelectedConflict] = useState(null);
  const [narrating, setNarrating] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);

  useEffect(() => {
    if (report) return; // already have it
    setLoading(true);
    fetch(`/api/reports/${encodeURIComponent(scriptId)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Report not found (${res.status})`);
        return res.json();
      })
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [scriptId, report]);

  const handleNarrate = async () => {
    if (!report) return;
    setNarrating(true);
    try {
      const res = await fetch(`/api/reports/${encodeURIComponent(scriptId)}/narrate`);
      if (!res.ok) throw new Error("Narration failed");
      const blob = await res.blob();
      setAudioUrl(URL.createObjectURL(blob));
    } catch (e) {
      setError(e.message);
    } finally {
      setNarrating(false);
    }
  };

  if (loading) {
    return (
      <main className="main-grid">
        <p className="muted">Loading report…</p>
      </main>
    );
  }

  if (error || !report) {
    return (
      <main className="main-grid">
        <motion.div className="panel error-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          {error || "Report not found."}
        </motion.div>
        <Link to="/reports" className="btn-secondary">
          Back to reports
        </Link>
      </main>
    );
  }

  return (
    <main className="main-grid">
      <ReportSummary report={report} onNarrate={handleNarrate} narrating={narrating} />
      {audioUrl && (
        <div className="panel audio-panel">
          <audio controls src={audioUrl} autoPlay />
        </div>
      )}
      <StoryTimeline report={report} onSelectConflict={setSelectedConflict} />
      <div className="split-grid">
        <ConflictList
          conflicts={report.conflicts}
          selected={selectedConflict}
          onSelect={setSelectedConflict}
        />
        <ClearanceList flags={report.clearance_flags} />
      </div>
      <ConflictDetail conflict={selectedConflict} onClose={() => setSelectedConflict(null)} />
    </main>
  );
}