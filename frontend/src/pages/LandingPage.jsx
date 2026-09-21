import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import "./LandingPage.css";

const FULL_HEADLINE = "Continuity gives your story a memory.";

/**
 * Wraps children in a div that fades/slides in once it scrolls into view.
 * Mirrors the .reveal / .reveal.in-view pattern from the original HTML page.
 */
function Reveal({ as: Tag = "div", className = "", children }) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setInView(true);
      return;
    }
    const el = ref.current;
    if (!el || !("IntersectionObserver" in window)) {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          io.unobserve(el);
        }
      },
      { threshold: 0.15 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <Tag ref={ref} className={`reveal ${inView ? "in-view" : ""} ${className}`}>
      {children}
    </Tag>
  );
}

/** Typewriter headline with a blinking cursor; renders instantly if reduced motion is preferred. */
function TypedHeadline() {
  const [typed, setTyped] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setTyped(FULL_HEADLINE);
      setDone(true);
      return;
    }
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setTyped(FULL_HEADLINE.slice(0, i));
      if (i >= FULL_HEADLINE.length) {
        clearInterval(interval);
        setDone(true);
      }
    }, 28);
    return () => clearInterval(interval);
  }, []);

  return (
    <h1 aria-label={FULL_HEADLINE}>
      {typed}
      {done && <span className="typed-cursor">&nbsp;</span>}
    </h1>
  );
}

/** Hero diagram card with a subtle mouse-tilt effect on pointer devices. */
function TiltCard({ className = "", children, ariaLabel }) {
  const ref = useRef(null);

  const handleMouseMove = (e) => {
    if (!window.matchMedia("(hover: hover)").matches || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    ref.current.style.transform = `perspective(600px) rotateY(${x * 4}deg) rotateX(${-y * 4}deg)`;
  };

  const handleMouseLeave = () => {
    if (ref.current) ref.current.style.transform = "perspective(600px) rotateY(0deg) rotateX(0deg)";
  };

  return (
    <div
      ref={ref}
      className={className}
      role="img"
      aria-label={ariaLabel}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {children}
    </div>
  );
}

const CHECK_ICON = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" strokeWidth="1.6" />
  </svg>
);

const CHECKLIST_ITEMS = [
  { title: "Contradictions", desc: "A fact one scene establishes that a later scene quietly breaks." },
  { title: "State violations", desc: "An object, injury, or costume detail that doesn't carry forward the way it should." },
  { title: "Unresolved threads", desc: "Something the script sets up and never pays off." },
  { title: "Legal clearance risks", desc: "Real people, brand names, and copyrighted references flagged before they reach a shoot." },
  { title: "A visual story timeline", desc: "Every tracked entity's state across every scene, at a glance." },
  { title: "A spoken report summary", desc: "The Supervisor's findings, read aloud." },
];

const TECH_STACK = [
  "LangGraph",
  "Groq · gpt-oss-120b / gpt-oss-20b",
  "FastAPI",
  "MongoDB Atlas",
  "React + Vite + Framer Motion",
  "gTTS voice narration",
];

export default function LandingPage() {
  return (
    <div className="landing-root">
      <div className="topbar">
        <div className="col">
          <Link to="/" className="brand">
            <span className="brand-mark">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 8L5 4H8L6 8H3Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
                <path d="M8 8L10 4H13L11 8H8Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
                <path d="M13 8L15 4H18L16 8H13Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
                <rect x="3" y="8" width="18" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
              </svg>
            </span>
            <span className="brand-name">CONTINUITY</span>
          </Link>
          <nav>
            <a href="#how-it-works">How it works</a>
            <a href="https://github.com/Abirami-2743/continuity">GitHub</a>
            <Link to="/analyze" className="nav-cta">Open app</Link>
          </nav>
        </div>
      </div>

      <main>
        <section className="hero">
          <div className="col">
            <p className="slug">
              FADE IN<span className="cursor"></span>
            </p>
            <TypedHeadline />
            <Reveal as="p" className="lede">
              A multi-agent system that reads every scene of a script and catches what a fast read misses
              — a necklace that vanishes, an injury that heals off-page, a claim one scene makes that
              another quietly breaks. It also flags real people, brands, and copyrighted references before
              they reach a shoot.
            </Reveal>
            <Reveal className="cta-row">
              <Link className="btn-primary" to="/analyze">
                Open app
              </Link>
              <a className="btn-secondary" href="https://github.com/Abirami-2743/continuity">
                <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
                </svg>
                View the code
              </a>
            </Reveal>

            <div className="hero-visual">
              <Reveal>
                <TiltCard
                  className="glass-card diagram"
                  ariaLabel="Diagram: Scene 12 shows a silver necklace, Scene 47 shows a bare neck, Continuity flags the contradiction"
                >
                  <svg viewBox="0 0 400 190" xmlns="http://www.w3.org/2000/svg">
                    <text x="10" y="22" className="scene-label">SCENE 12</text>
                    <text x="10" y="42" className="scene-text">SARAH adjusts a</text>
                    <text x="10" y="58" className="scene-text">silver necklace.</text>

                    <text x="220" y="22" className="scene-label">SCENE 47</text>
                    <text x="220" y="42" className="scene-text">Her neck is bare —</text>
                    <text x="220" y="58" className="scene-text">no jewelry visible.</text>

                    <ellipse className="flag-circle draw" cx="80" cy="52" rx="55" ry="13" />
                    <ellipse className="flag-circle draw" cx="290" cy="52" rx="62" ry="13" />
                    <path className="flag-line draw" d="M135,52 C 170,52 210,52 228,52" strokeDasharray="6 5" />

                    <g className="fade-in-tag">
                      <rect x="90" y="82" width="150" height="24" fill="var(--flag-red-soft)" rx="4" />
                      <text x="165" y="98" className="flag-tag" textAnchor="middle">
                        CONTRADICTION FLAGGED
                      </text>
                    </g>
                    <text x="165" y="128" className="scene-label fade-in-tag" textAnchor="middle">
                      requires human review
                    </text>
                  </svg>
                </TiltCard>
              </Reveal>

              <Reveal className="glass-card badge-card float-y">
                <span className="eyebrow">SAMPLE OUTPUT</span>
                <div className="mock-flag-row">
                  <span className="mock-flag-text">Necklace vanishes S12→S47</span>
                  <span className="badge badge-high">High</span>
                </div>
                <div className="mock-flag-row">
                  <span className="mock-flag-text">Bruise heals early S8→S9</span>
                  <span className="badge badge-medium">Medium</span>
                </div>
                <div className="mock-flag-row">
                  <span className="mock-flag-text">Setup gun never fired</span>
                  <span className="badge badge-low">Low</span>
                </div>
                <span className="mock-flag-conf">Every flag ships with a confidence score and source scenes.</span>
              </Reveal>
            </div>
          </div>
        </section>

        <section id="the-problem">
          <Reveal as="div" className="col">
            <h2 className="scene-heading">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.6" />
                <path d="M20 20L16.5 16.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              INT. THE PROBLEM — CONTINUOUS
            </h2>
            <p>
              Even well-resourced productions ship continuity errors. Checking consistency across
              hundreds of pages and dozens of scenes still depends on someone's memory — an assistant
              director or script supervisor flipping back through pages during a night shoot. Continuity
              turns that manual check into something systematic and auditable, without pretending to
              replace the person doing the checking.
            </p>
          </Reveal>
        </section>

        <section id="how-it-works">
          <Reveal as="div" className="col">
            <h2 className="scene-heading">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.6" />
                <path d="M3 9H21" stroke="currentColor" strokeWidth="1.6" />
                <path d="M8 4V9" stroke="currentColor" strokeWidth="1.6" />
              </svg>
              INT. HOW IT WORKS — DAY
            </h2>
            <p>Four agents, each with one job, orchestrated as a LangGraph state graph.</p>
            <div className="sheet">
              <div className="sheet-row">
                <div className="sheet-role">EXTRACTOR</div>
                <div>
                  <p className="sheet-desc">
                    Reads each scene and pulls out structured facts — who's there, what they look like,
                    what state props are in, any real-world references.
                  </p>
                </div>
              </div>
              <div className="sheet-row">
                <div className="sheet-role">COMPARATOR</div>
                <div>
                  <p className="sheet-desc">
                    Reasons across each character's or prop's entire scene history at once, flagging
                    contradictions, state violations, and unresolved threads — with a confidence score
                    and the exact source scenes attached to every flag.
                  </p>
                  <p className="sheet-note">
                    Grounded in a deterministic first pass: a plain-Python step decides which entities
                    actually recur across scenes before any LLM is called, so every flag traces back to a
                    real candidate, not an opaque decision.
                  </p>
                </div>
              </div>
              <div className="sheet-row">
                <div className="sheet-role">LEGAL CLEARANCE</div>
                <div>
                  <p className="sheet-desc">
                    Checks for real people, brands, and copyrighted material that would need clearance
                    before production.
                  </p>
                </div>
              </div>
              <div className="sheet-row">
                <div className="sheet-role">SUPERVISOR</div>
                <div>
                  <p className="sheet-desc">
                    Orchestrates the pipeline and compiles every other agent's findings into one report —
                    including a spoken summary you can play back.
                  </p>
                </div>
              </div>
            </div>
          </Reveal>
        </section>

        <section id="what-it-catches">
          <Reveal as="div" className="col">
            <h2 className="scene-heading">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M5 12L10 17L19 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              INT. WHAT IT CATCHES — CONTINUOUS
            </h2>
            <ul className="checklist">
              {CHECKLIST_ITEMS.map((item) => (
                <li key={item.title}>
                  <span className="check-icon">{CHECK_ICON}</span>
                  <span>
                    <strong>{item.title}</strong>
                    <span className="desc">{item.desc}</span>
                  </span>
                </li>
              ))}
            </ul>
          </Reveal>
        </section>

        <section id="why">
          <Reveal as="div" className="col">
            <h2 className="scene-heading">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 2L14.5 8.5L21 9.3L16 13.9L17.4 20.5L12 17L6.6 20.5L8 13.9L3 9.3L9.5 8.5L12 2Z"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinejoin="round"
                />
              </svg>
              INT. WHY THESE CHOICES — DAY
            </h2>
            <p>
              Continuity-checking genuinely splits into distinct skills — extraction, comparison, legal
              judgment — so separating them into agents made each one independently promptable,
              testable, and debuggable. An earlier design compared every scene pair directly; batching by
              entity instead fixed both the token budget and the inability to reason across more than two
              scenes at once.
            </p>
            <p>
              The system never asserts a verdict. Every flag ships with a confidence score and a
              "requires human review" status — it's built to surface evidence, not replace a script
              supervisor's judgment.
            </p>
          </Reveal>
        </section>

        <section id="stack">
          <Reveal as="div" className="col">
            <h2 className="scene-heading">TECH STACK</h2>
            <div className="tech-strip">
              {TECH_STACK.map((chip) => (
                <span className="tech-chip" key={chip}>
                  {chip}
                </span>
              ))}
            </div>
          </Reveal>
        </section>
      </main>

      <footer>
        <Reveal as="div" className="col">
          <p className="fade-out">FADE OUT.</p>
          <p className="footer-line">
            Built for The Great Agent Hackathon (Track 3: AI-native Enterprise, open stack). Every flag
            is evidence for a human to review, not an automated verdict.
          </p>
          <div className="footer-cta">
            <a className="btn-secondary" href="https://github.com/Abirami-2743/continuity">
              View on GitHub
            </a>
          </div>
        </Reveal>
      </footer>
    </div>
  );
}