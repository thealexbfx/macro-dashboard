import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

const Chart = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={data} margin={{ top: 20, right: 30, bottom: 20, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="date"
          tickFormatter={(str) => {
            const date = new Date(str);
            return `${date.getMonth() + 1}/${date.getFullYear().toString().slice(-2)}`;
          }}
        />
        <YAxis />
        <Tooltip
          labelFormatter={(label) => `Date: ${label}`}
          formatter={(value) => [`${value}%`, 'CPI']}
        />
        <Line type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={3} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default Chart;
