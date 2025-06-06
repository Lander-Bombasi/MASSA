import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import ScalePage from "./pages/ScalePage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ScalePage />} />
      </Routes>
    </Router>
  );
}

export default App;
