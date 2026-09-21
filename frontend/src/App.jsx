import { Routes, Route, Outlet } from "react-router-dom";
import Header from "./components/Header.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import ReportsListPage from "./pages/ReportsListPage.jsx";
import ReportDetailPage from "./pages/ReportDetailPage.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import "./App.css";

// The tool's own pages share the app-shell + Header. The landing page is
// full-bleed with its own header/nav, so it sits outside this layout and
// owns the root path.
function AppLayout() {
  return (
    <div className="app-shell">
      <Header />
      <Outlet />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route element={<AppLayout />}>
        <Route path="/analyze" element={<UploadPage />} />
        <Route path="/reports" element={<ReportsListPage />} />
        <Route path="/reports/:scriptId" element={<ReportDetailPage />} />
      </Route>
    </Routes>
  );
}