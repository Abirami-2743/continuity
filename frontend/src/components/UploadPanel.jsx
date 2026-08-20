import { useState, useEffect } from "react";
import { motion } from "framer-motion";

export default function UploadPanel({ onAnalyze, loading }) {
  const [scriptId, setScriptId] = useState("");
  const [scenesText, setScenesText] = useState("");
  const [demos, setDemos] = useState([]);
  const [selectedDemo, setSelectedDemo] = useState("");

  useEffect(() => {
    fetch("/sample_scripts/manifest.json")
      .then((res) => res.json())
      .then((data) => {
        setDemos(data.demos || []);
        if (data.demos?.length) setSelectedDemo(data.demos[0].id);
      })
      .catch(() => setDemos([])); // manifest missing is non-fatal — manual paste still works
  }, []);

  const handleSubmit = () => {
    const scenes = scenesText
      .split(/\n---\n/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!scriptId.trim() || scenes.length === 0) return;
    onAnalyze(scriptId.trim(), scenes);
  };

  const loadSample = async () => {
    const demo = demos.find((d) => d.id === selectedDemo);
    if (!demo) return;
    const res = await fetch(`/sample_scripts/${demo.file}`);
    const data = await res.json();
    setScriptId(data.script_id);
    setScenesText(data.scenes.join("\n---\n"));
  };

  return (
    <motion.div
      className="panel upload-panel"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <span className="eyebrow">Step 1</span>
      <h3>Upload a script</h3>
      <p className="muted">
        Paste each scene separated by a line containing <code>---</code>, or load one of
        the planted-inconsistency demo sets below to see the pipeline run against known
        ground truth, at increasing difficulty.
      </p>

      {demos.length > 0 && (
        <>
          <label className="field-label" htmlFor="demo-select">
            Demo set
          </label>
          <div className="demo-picker-row">
            <select
              id="demo-select"
              className="text-input demo-select"
              value={selectedDemo}
              onChange={(e) => setSelectedDemo(e.target.value)}
            >
              {demos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title} — {d.difficulty}
                </option>
              ))}
            </select>
            <button className="btn-secondary" onClick={loadSample} type="button">
              Load
            </button>
          </div>
          {demos.find((d) => d.id === selectedDemo) && (
            <p className="muted demo-description">
              {demos.find((d) => d.id === selectedDemo).description}
            </p>
          )}
        </>
      )}

      <label className="field-label" htmlFor="script-id">
        Script ID
      </label>
      <input
        id="script-id"
        className="text-input"
        placeholder="e.g. maya-demo"
        value={scriptId}
        onChange={(e) => setScriptId(e.target.value)}
      />

      <label className="field-label" htmlFor="scenes">
        Scenes
      </label>
      <textarea
        id="scenes"
        className="scene-input"
        placeholder="EPISODE 1, SCENE 1 - INT. CABIN - NIGHT. ...&#10;---&#10;EPISODE 1, SCENE 2 - ..."
        value={scenesText}
        onChange={(e) => setScenesText(e.target.value)}
        rows={10}
      />

      <div className="button-row">
        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={loading}
          type="button"
        >
          {loading ? "Analyzing…" : "Run Continuity"}
        </button>
      </div>
    </motion.div>
  );
}