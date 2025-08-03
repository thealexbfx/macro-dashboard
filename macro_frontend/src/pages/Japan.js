import React, { useEffect, useState } from "react";
import Chart from "../components/Chart";

const Japan = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/japan/cpi")
      .then((res) => res.json())
      .then((json) => {
        setData(json.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch data", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-3xl font-semibold text-gray-900">Japan Consumer Price Index (CPI)</h2>
        <p className="text-gray-600 mt-1 max-w-xl">
          This chart visualizes the quarter-on-quarter change in Japan's CPI, giving insights into inflation trends.
        </p>
      </header>

      <section className="bg-white rounded-xl shadow border border-gray-200 p-6 min-h-[320px]">
        {loading ? (
          <div className="flex justify-center items-center h-full text-gray-400">Loading data...</div>
        ) : data.length === 0 ? (
          <div className="text-center text-gray-500">No data available.</div>
        ) : (
          <Chart data={data} />
        )}
      </section>
    </div>
  );
};

export default Japan;
