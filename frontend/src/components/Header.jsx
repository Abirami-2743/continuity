import { motion } from "framer-motion";
import { NavLink } from "react-router-dom";

export default function Header() {
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
      <nav className="main-nav">
        <NavLink to="/analyze" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
          Analyze
        </NavLink>
        <NavLink to="/reports" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
          Reports
        </NavLink>
        <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
          Home
        </NavLink>
      </nav>
    </motion.header>
  );
}