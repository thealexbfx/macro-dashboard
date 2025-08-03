import { Link } from 'react-router-dom';
import { useState } from 'react';

const Navbar = () => {
  const [openMenu, setOpenMenu] = useState(null);

  const toggleMenu = (menu) => {
    setOpenMenu(openMenu === menu ? null : menu);
  };

  return (
    <nav className="bg-gray-900 text-white px-8 py-4 flex justify-between items-center shadow-lg sticky top-0 z-50">
      <div className="text-2xl font-bold tracking-widest">
        <Link to="/">THEALEXBFX</Link>
      </div>

      <ul className="flex space-x-8 font-medium text-sm">
        <li>
          <Link to="/" className="hover:text-yellow-400">Home</Link>
        </li>

        <li className="relative">
          <button
            onClick={() => toggleMenu('countries')}
            className="hover:text-yellow-400 flex items-center"
          >
            Countries
            <svg
              className="ml-1 w-3 h-3"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {openMenu === 'countries' && (
            <ul className="absolute top-full left-0 mt-2 w-40 bg-gray-800 rounded shadow-lg">
              <li>
                <Link to="/usa" className="block px-4 py-2 hover:bg-yellow-400 hover:text-black">
                  USA
                </Link>
              </li>
              <li>
                <Link to="/japan" className="block px-4 py-2 hover:bg-yellow-400 hover:text-black">
                  Japan
                </Link>
              </li>
              <li>
                <Link to="/uk" className="block px-4 py-2 hover:bg-yellow-400 hover:text-black">
                  UK
                </Link>
              </li>
              <li>
                <Link to="/euro-area" className="block px-4 py-2 hover:bg-yellow-400 hover:text-black">
                  Euro Area
                </Link>
              </li>
            </ul>
          )}
        </li>

        <li>
          <Link to="/fx-rates" className="hover:text-yellow-400">FX Rates</Link>
        </li>

        <li>
          <Link to="/compare" className="hover:text-yellow-400">Compare</Link>
        </li>

        <li>
          <Link to="/calendar" className="hover:text-yellow-400">Calendar</Link>
        </li>
      </ul>
    </nav>
  );
};

export default Navbar;
