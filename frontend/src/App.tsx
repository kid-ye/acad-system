import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Masthead from "./components/Masthead";
import Home from "./routes/Home";
import Ask from "./routes/Ask";

// Code-split the heavy routes out of the first-paint bundle: Stats pulls in
// `reaviz` (charts) and Download pulls in `@tanstack/react-table`. Home and Ask
// stay eager so the common path and the LCP-critical hero are not gated on a
// chunk fetch.
const Stats = lazy(() => import("./routes/Stats"));
const Download = lazy(() => import("./routes/Download"));

export default function App() {
  // Home's hero fills the viewport under the fixed nav on purpose (the pill
  // floats over the image); every other screen needs room reserved for it.
  const needsNavGap = useLocation().pathname !== "/home";

  return (
    <div className="min-h-screen">
      <Masthead />
      <div className={needsNavGap ? "pt-[76px]" : ""}>
        <Suspense fallback={<div className="p-8 text-sm text-muted-foreground">Loading…</div>}>
          <Routes>
            <Route path="/home" element={<Home />} />
            <Route path="/ask" element={<Ask />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/download" element={<Download />} />
            <Route path="*" element={<Navigate to="/home" replace />} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}
