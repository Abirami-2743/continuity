import { motion } from "framer-motion";

/**
 * Signature element: a continuity sheet. Columns = scenes, rows = entities
 * (characters/props) that recur across scenes. Every cell value comes
 * straight from the Extractor Agent's structured output (report.scene_facts)
 * — nothing here is inferred or parsed client-side. A red flag marks any
 * cell pair the Comparator Agent actually flagged as a conflict.
 */
export default function StoryTimeline({ report, onSelectConflict }) {
  if (!report || report.scene_facts.length === 0) return null;

  const scenes = report.scene_facts;
  const rows = buildRows(scenes);

  return (
    <div className="timeline">
      <div className="timeline-head">
        <span className="eyebrow">Story timeline</span>
        <h3>Tracked entities across scenes</h3>
      </div>

      <div
        className="timeline-scroll timeline-grid"
        style={{ gridTemplateColumns: `170px repeat(${scenes.length}, 1fr)` }}
      >
        <div className="timeline-corner" />
        {scenes.map((s) => (
          <div key={s.scene_id} className="timeline-col-label">
            {s.scene_id.replace(/^.*-scene-/, "Scene ")}
          </div>
        ))}

        {rows.map((row) => (
          <Row
            key={row.key}
            row={row}
            scenes={scenes}
            report={report}
            onSelectConflict={onSelectConflict}
          />
        ))}
      </div>
    </div>
  );
}

function Row({ row, scenes, report, onSelectConflict }) {
  return (
    <>
      <div className="timeline-row-label">{row.label}</div>
      {scenes.map((scene) => {
        const cell = row.bySceneId[scene.scene_id];
        // Match on BOTH scene membership AND entity name — matching scene
        // alone caused unrelated rows to light up red whenever they shared
        // a scene with a conflict about a totally different entity.
        const conflict = report.conflicts.find(
          (c) =>
            c.entity_name &&
            row.label.toLowerCase().includes(c.entity_name.toLowerCase()) &&
            c.source_scene_ids.includes(scene.scene_id)
        );
        return (
          <motion.button
            key={scene.scene_id}
            className={`timeline-cell ${conflict ? "flagged" : cell ? "known" : "empty"}`}
            whileHover={cell ? { scale: 1.04 } : {}}
            disabled={!conflict}
            onClick={() => conflict && onSelectConflict(conflict)}
          >
            {cell || "—"}
            {conflict && <span className="flag-dot" />}
          </motion.button>
        );
      })}
    </>
  );
}

function buildRows(scenes) {
  const rows = new Map();

  scenes.forEach((scene) => {
    scene.characters.forEach((c) => {
      const key = `character:${c.name.toLowerCase()}`;
      if (!rows.has(key)) rows.set(key, { key, label: c.name, bySceneId: {} });
      const parts = [c.appearance, c.status !== "unknown" ? c.status : null].filter(Boolean);
      rows.get(key).bySceneId[scene.scene_id] = parts.join(" · ");
    });
    scene.props.forEach((p) => {
      const key = `prop:${p.name.toLowerCase()}`;
      if (!rows.has(key)) rows.set(key, { key, label: p.name, bySceneId: {} });
      rows.get(key).bySceneId[scene.scene_id] = p.state !== "unknown" ? p.state : null;
    });
  });

  // Only keep rows that appear in 2+ scenes — those are the ones that can
  // meaningfully show continuity across the timeline.
  return Array.from(rows.values()).filter(
    (row) => Object.keys(row.bySceneId).length >= 2
  );
}