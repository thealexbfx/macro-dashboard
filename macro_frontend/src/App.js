import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import MainLayout from "./components/MainLayout";
import Home from "./pages/Home";
import Japan from "./pages/Japan";

function App() {
  return (
    <Router>
      <MainLayout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/japan" element={<Japan />} />
          {/* Add more routes here */}
        </Routes>
      </MainLayout>
    </Router>
  );
}

export default App;
