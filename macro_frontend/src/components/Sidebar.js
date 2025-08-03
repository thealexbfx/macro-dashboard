import React from "react";
import { Home, LineChart, TrendingUp, DollarSign } from "lucide-react";

const Sidebar = () => {
  return (
    <div className="w-full h-full bg-gray-900 text-white flex flex-col">
      {/* Logo / Brand */}
      <div className="p-6 text-xl font-semibold border-b border-gray-700 tracking-wide">
        thealexbfx
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-4 text-sm">
        <SidebarLink icon={<Home size={18} />} label="Dashboard" href="/" />
        <SidebarLink icon={<TrendingUp size={18} />} label="Japan CPI" href="/japan" />
        <SidebarLink icon={<LineChart size={18} />} label="US CPI" href="/us-cpi" />
        <SidebarLink icon={<DollarSign size={18} />} label="Interest Rates" href="/rates" />
      </nav>
    </div>
  );
};

const SidebarLink = ({ icon, label, href }) => (
  <a
    href={href}
    className="flex items-center gap-2 px-3 py-2 rounded hover:bg-gray-700 transition-colors"
  >
    {icon}
    <span>{label}</span>
  </a>
);

export default Sidebar;
