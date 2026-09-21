import { useState } from "react";
import { useNavigate } from "react-router-dom";
import UploadPanel from "../components/UploadPanel.jsx";

// TODO: change this to match your backend's analyze endpoint.
const ANALYZE_URL = "/api/analyze";

export default function UploadPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async (scriptId, scenes) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(ANALYZE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // TODO: match the payload shape your backend expects.
        body: JSON.stringify({ script_id: scriptId, scenes }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`Server returned ${res.status}${detail ? `: ${detail}` : ""}`);
      }
      // Go to the report for this script once analysis finishes.
      navigate(`/reports/${encodeURIComponent(scriptId)}`);
    } catch (err) {
      console.error("Analyze failed:", err);
      setError(err.message || "Something went wrong while analyzing the script.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <UploadPanel onAnalyze={handleAnalyze} loading={loading} />
      {error && <p className="muted">Analysis failed: {error}</p>}
    </>
  );
}