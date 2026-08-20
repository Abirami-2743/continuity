import { useState } from "react";
import { motion } from "framer-motion";
import UploadPanel from "./components/UploadPanel.jsx";
import ReportSummary from "./components/ReportSummary.jsx";
import StoryTimeline from "./components/StoryTimeline.jsx";
import { ConflictList, ClearanceList, ConflictDetail } from "./components/ConflictPanels.jsx";
import "./App.css";

export default function App() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedConflict, setSelectedConflict] = useState(null);
  const [narrating, setNarrating] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);

  const runAnalysis = async (scriptId, scenes) => {
    setLoading(true);
    setError(null);
    setReport(null);
    setSelectedConflict(null);
    setAudioUrl(null);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script_id: scriptId, scenes }),
      });
      if (!res.ok) throw new Error(`Analysis failed (${res.status})`);
      const data = await res.json();
      setReport(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNarrate = async () => {
    if (!report) return;
    setNarrating(true);
    try {
      const res = await fetch(`/api/reports/${report.script_ids[0]}/narrate`);
      if (!res.ok) throw new Error("Narration failed");
      const blob = await res.blob();
      setAudioUrl(URL.createObjectURL(blob));
    } catch (e) {
      setError(e.message);
    } finally {
      setNarrating(false);
    }
  };

  return (
    <div className="app-shell">
      <Header />

      <main className="main-grid">
        <UploadPanel onAnalyze={runAnalysis} loading={loading} />

        {error && (
          <motion.div className="panel error-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {error}
          </motion.div>
        )}

        {report && (
          <>
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
          </>
        )}
      </main>

      <ConflictDetail conflict={selectedConflict} onClose={() => setSelectedConflict(null)} />
    </div>
  );
}

function Header() {
  return (
    <motion.header
      className="app-header"
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="brand">
        <span className="brand-mark">¶</span>
        <span className="brand-name">Continuity</span>
      </div>
      <p className="tagline">Continuity gives your story a memory.</p>
    </motion.header>
  );
}
