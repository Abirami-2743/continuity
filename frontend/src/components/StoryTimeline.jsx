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

  const merged = mergeNearDuplicateRows(rows);

  // Only keep rows that appear in 2+ scenes — those are the ones that can
  // meaningfully show continuity across the timeline.
  return Array.from(merged.values()).filter(
    (row) => Object.keys(row.bySceneId).length >= 2
  );
}

function mergeNearDuplicateRows(rows) {
  // Mirrors the backend's _merge_near_duplicate_names in comparator.py —
  // the Extractor reads each scene independently, so "ring" in one scene
  // and "gold ring" in another arrive as separate rows even though they're
  // the same object. Merge same-type rows where one label's words are
  // fully contained in the other's (word-boundary check, so "ring" merges
  // into "gold ring" but NOT into "earring" — different words entirely).
  const keys = Array.from(rows.keys());
  const parent = new Map(keys.map((k) => [k, k]));

  const find = (k) => {
    while (parent.get(k) !== k) k = parent.get(k);
    return k;
  };

  for (let i = 0; i < keys.length; i++) {
    for (let j = i + 1; j < keys.length; j++) {
      const [type1] = keys[i].split(":");
      const [type2] = keys[j].split(":");
      if (type1 !== type2) continue;

      const words1 = new Set(rows.get(keys[i]).label.toLowerCase().split(/\s+/));
      const words2 = new Set(rows.get(keys[j]).label.toLowerCase().split(/\s+/));
      const isSubset = (a, b) => [...a].every((w) => b.has(w));

      if (words1.size && words2.size && (isSubset(words1, words2) || isSubset(words2, words1))) {
        const bigger = words1.size >= words2.size ? keys[i] : keys[j];
        const smaller = bigger === keys[i] ? keys[j] : keys[i];
        parent.set(find(smaller), find(bigger));
      }
    }
  }

  const merged = new Map();
  keys.forEach((k) => {
    const root = find(k);
    if (!merged.has(root)) {
      merged.set(root, { ...rows.get(root), bySceneId: {} });
    }
    Object.assign(merged.get(root).bySceneId, rows.get(k).bySceneId);
  });
  return merged;
}