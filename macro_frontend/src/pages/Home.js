// src/pages/Home.js
import React from "react";
import { LineChart, TrendingUp, BarChart3 } from "lucide-react";

const Home = () => {
  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <div>
        <h1 className="text-3xl font-semibold text-gray-900">Welcome to thealexbfx Macro Dashboard</h1>
        <p className="text-gray-600 mt-1">Track global macroeconomic indicators, visualize FX trends, and compare data across countries.</p>
      </div>

      {/* Key Indicators Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <IndicatorCard
          title="Global CPI Trends"
          icon={<TrendingUp className="text-blue-600" />}
          description="See how inflation is shifting across regions."
        />
        <IndicatorCard
          title="Currency Charts"
          icon={<LineChart className="text-green-600" />}
          description="Track FX rates and historical performance."
        />
        <IndicatorCard
          title="Interest Rate Monitor"
          icon={<BarChart3 className="text-purple-600" />}
          description="Follow central bank rate decisions in real time."
        />
      </div>

      {/* Chart Preview Placeholder */}
      <div className="bg-white rounded-xl shadow p-6 border border-gray-200">
        <h2 className="text-xl font-medium mb-4">Recent CPI Movement (Preview)</h2>
        <div className="h-64 flex items-center justify-center text-gray-400">
          {/* Replace with real chart later */}
          [Chart goes here]
        </div>
      </div>
    </div>
  );
};

const IndicatorCard = ({ title, icon, description }) => (
  <div className="bg-white border border-gray-200 rounded-xl p-4 shadow hover:shadow-md transition">
    <div className="flex items-center gap-3">
      <div className="p-2 bg-gray-100 rounded-full">{icon}</div>
      <div>
        <h3 className="text-md font-semibold text-gray-800">{title}</h3>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
    </div>
  </div>
);

export default Home;
