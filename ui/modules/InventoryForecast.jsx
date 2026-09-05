import React, { useState, useEffect } from 'react';
import { TrendingDown, AlertCircle, CheckCircle, Info } from 'lucide-react';

/**
 * PolarOS Inventory Forecast Module
 *
 * Reads from season.db using sql.js (browser-based SQLite)
 * Shows stock levels, burn rates, and projected zero-dates
 * RED = stock runs out before resupply ship
 * GREEN = stock safe until next resupply
 */

export default function InventoryForecast() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [asOf, setAsOf] = useState('2027-09-15T23:59:59Z'); // demo date
  const [resupply, setResupply] = useState('2027-12-15');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // For development: fetch pre-generated JSON from the queries
        // In production, you'd use sql.js to load season.db and run the query
        const response = await fetch('/api/burnrate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ as_of: asOf, resupply })
        });

        if (!response.ok) {
          throw new Error('Failed to fetch burnrate data');
        }

        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        console.error('Error:', err);
        setError(err.message);
        // Fallback: load hardcoded demo data
        setData(getDemoData());
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [asOf, resupply]);

  const getDemoData = () => {
    // Hardcoded demo data from q_burnrate.sql output
    return [
      {
        station: 'MAITRI',
        category: 'diesel',
        qty_on_hand: 2255.44,
        unit: 'L',
        avg_daily_28d: 128.58,
        days_of_cover: 17.5,
        projected_zero_date: '2027-10-02',
        next_resupply: '2027-12-15',
        days_short_of_ship: -74,
        status: 'RED',
        forecast_made_at: '2027-09-15T23:59:59Z'
      },
      {
        station: 'BHARATI',
        category: 'diesel',
        qty_on_hand: 11806.7,
        unit: 'L',
        avg_daily_28d: 89.54,
        days_of_cover: 131.9,
        projected_zero_date: '2028-01-24',
        next_resupply: '2027-12-15',
        days_short_of_ship: 40,
        status: 'GREEN',
        forecast_made_at: '2027-09-15T23:59:59Z'
      },
      {
        station: 'MAITRI',
        category: 'food',
        qty_on_hand: 3239.78,
        unit: 'kg',
        avg_daily_28d: 21.44,
        days_of_cover: 151.1,
        projected_zero_date: '2028-02-13',
        next_resupply: '2027-12-15',
        days_short_of_ship: 60,
        status: 'GREEN',
        forecast_made_at: '2027-09-15T23:59:59Z'
      },
      {
        station: 'BHARATI',
        category: 'food',
        qty_on_hand: 2169.05,
        unit: 'kg',
        avg_daily_28d: 15.37,
        days_of_cover: 141.1,
        projected_zero_date: '2028-02-03',
        next_resupply: '2027-12-15',
        days_short_of_ship: 50,
        status: 'GREEN',
        forecast_made_at: '2027-09-15T23:59:59Z'
      }
    ];
  };

  const redItems = data.filter(d => d.status === 'RED');
  const greenItems = data.filter(d => d.status === 'GREEN');
  const noDataItems = data.filter(d => d.status === 'NO DATA');

  const formatDate = (dateStr) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            📦 Inventory Forecast
          </h1>
          <p className="text-slate-300 text-sm md:text-base">
            Stock levels, burn rates, and projected zero-dates for all stations
          </p>
        </div>

        {/* Forecast Date Info */}
        <div className="bg-slate-700 bg-opacity-50 rounded-lg p-4 mb-6 border border-slate-600">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-slate-300 text-sm font-semibold">Forecast As Of:</label>
              <p className="text-white font-mono text-sm mt-1">{formatDate(asOf)}</p>
              <p className="text-slate-400 text-xs mt-1">Alert fired: 29 March 2027 (190 days before crisis)</p>
            </div>
            <div>
              <label className="text-slate-300 text-sm font-semibold">Next Resupply:</label>
              <p className="text-white font-mono text-sm mt-1">{formatDate(resupply)}</p>
              <p className="text-slate-400 text-xs mt-1">Ship expected mid-December</p>
            </div>
          </div>
        </div>

        {/* RED Alert Section */}
        {redItems.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <AlertCircle className="text-red-500" size={24} />
              <h2 className="text-2xl font-bold text-red-500">
                Critical: Stock Running Out
              </h2>
            </div>
            <div className="space-y-4">
              {redItems.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-red-900 bg-opacity-30 border-2 border-red-500 rounded-lg p-5 md:p-6"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl md:text-2xl font-bold text-white">
                        {item.station} — {item.category.toUpperCase()}
                      </h3>
                      <p className="text-red-300 text-sm mt-1">
                        🚨 Runs out before ship arrives
                      </p>
                    </div>
                    <span className="bg-red-600 text-white px-3 py-1 rounded-full text-xs md:text-sm font-bold">
                      {item.days_short_of_ship} days SHORT
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <p className="text-slate-400 text-xs md:text-sm">On Hand</p>
                      <p className="text-white font-bold text-lg md:text-xl">
                        {item.qty_on_hand.toLocaleString('en-IN', {
                          maximumFractionDigits: 1
                        })}
                        <span className="text-sm text-slate-300 ml-1">{item.unit}</span>
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-400 text-xs md:text-sm">Daily Burn</p>
                      <p className="text-white font-bold text-lg md:text-xl">
                        {item.avg_daily_28d.toLocaleString('en-IN', {
                          maximumFractionDigits: 1
                        })}
                        <span className="text-sm text-slate-300 ml-1">{item.unit}/day</span>
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-400 text-xs md:text-sm">Days of Cover</p>
                      <p className="text-red-300 font-bold text-lg md:text-xl">
                        {item.days_of_cover.toFixed(1)} days
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-400 text-xs md:text-sm">Zero Date</p>
                      <p className="text-red-300 font-bold text-lg md:text-xl">
                        {formatDate(item.projected_zero_date)}
                      </p>
                    </div>
                  </div>

                  {/* Burn Rate Visualization */}
                  <div className="relative h-12 bg-slate-800 rounded overflow-hidden border border-slate-700">
                    <div
                      className="absolute top-0 left-0 h-full bg-gradient-to-r from-orange-500 to-red-600 transition-all duration-500"
                      style={{
                        width: `${Math.min(100, (100 - item.days_of_cover / 1.5))}%`
                      }}
                    >
                      <div className="h-full flex items-center justify-center">
                        <span className="text-white font-bold text-xs md:text-sm drop-shadow">
                          {Math.round((100 - item.days_of_cover / 1.5))}% consumed
                        </span>
                      </div>
                    </div>
                  </div>

                  <p className="text-slate-400 text-xs mt-3">
                    Based on 28-day trailing average consumption
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* GREEN Section */}
        {greenItems.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="text-green-500" size={24} />
              <h2 className="text-2xl font-bold text-green-500">
                Safe: Stock Sufficient Until Resupply
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {greenItems.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-green-900 bg-opacity-20 border border-green-600 rounded-lg p-4 md:p-5"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="text-lg font-bold text-white">
                        {item.station} — {item.category}
                      </h4>
                      <p className="text-green-300 text-xs md:text-sm mt-1">
                        ✓ Safe margin: +{item.days_short_of_ship} days
                      </p>
                    </div>
                    <span className="bg-green-600 text-white px-2 py-1 rounded text-xs font-bold">
                      {item.days_of_cover.toFixed(0)}d
                    </span>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">On Hand:</span>
                      <span className="text-white font-mono">
                        {item.qty_on_hand.toLocaleString('en-IN', {
                          maximumFractionDigits: 0
                        })} {item.unit}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Burn Rate:</span>
                      <span className="text-white font-mono">
                        {item.avg_daily_28d.toFixed(1)} {item.unit}/day
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Zero Date:</span>
                      <span className="text-green-300 font-mono">
                        {formatDate(item.projected_zero_date)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No Data Section */}
        {noDataItems.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Info className="text-slate-400" size={24} />
              <h2 className="text-xl font-bold text-slate-400">
                No Consumption Data
              </h2>
            </div>
            <div className="bg-slate-800 bg-opacity-50 border border-slate-600 rounded-lg p-4">
              <p className="text-slate-300 text-sm mb-3">
                These items have no consumption history in the past 28 days:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {noDataItems.map((item, idx) => (
                  <div key={idx} className="text-slate-400 text-sm">
                    • {item.station} — {item.category} ({item.qty_on_hand.toLocaleString('en-IN', {
                      maximumFractionDigits: 0
                    })} {item.unit})
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Info Box */}
        <div className="bg-blue-900 bg-opacity-30 border border-blue-600 rounded-lg p-4 md:p-5 mt-6">
          <h3 className="text-white font-bold mb-2 flex items-center gap-2">
            <Info size={18} />
            Why This Matters
          </h3>
          <ul className="text-slate-300 text-sm space-y-2">
            <li>• <strong>RED items</strong> require immediate action — we discovered this 190 days early (29 March alert for October crisis)</li>
            <li>• <strong>Burn rate</strong> is a 28-day trailing average, not an estimate</li>
            <li>• <strong>Forecast date</strong> is based on the log as of 15 Sep — no access to future events</li>
            <li>• Ship arrives 15 December; anything running out before then is RED</li>
          </ul>
        </div>

        {/* Debug Info */}
        {error && (
          <div className="mt-6 bg-yellow-900 bg-opacity-30 border border-yellow-600 rounded-lg p-4">
            <p className="text-yellow-300 text-sm">
              <strong>Demo mode:</strong> {error} — using hardcoded data
            </p>
          </div>
        )}

        {loading && (
          <div className="mt-6 text-center">
            <p className="text-slate-400">Loading forecast...</p>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * STYLING GUIDE for other modules:
 *
 * Color scheme:
 * - RED alert: bg-red-900 border-red-500 text-red-300/500
 * - GREEN safe: bg-green-900 border-green-600 text-green-300/500
 * - Background: slate-900 to slate-800
 * - Text: white on dark, slate-300 for secondary
 *
 * Layout:
 * - Mobile-first: single column on small screens
 * - Grid on medium+: 2-4 columns
 * - Min touch target: 44x44px
 *
 * Data pattern:
 * 1. Fetch from API or localStorage
 * 2. Filter by status (RED first, then GREEN)
 * 3. Map to card components
 * 4. Show fallback demo data if network fails
 */
