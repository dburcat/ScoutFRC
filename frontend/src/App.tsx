import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import LoginPage from '@/pages/LoginPage';
import api from '@/api/axios';

function App() {
  const auth = useAuth();
  const user = auth?.user;
  const logout = auth?.logout;
  const isLoadingAuth = auth?.isLoading;

  const [showLogin, setShowLogin] = useState(false);
  const [scoutingData, setScoutingData] = useState<any[]>([]);

  useEffect(() => {
    api.get('/matches/')
      .then(res => {
        console.log("Matches received:", res.data);
        setScoutingData(res.data);
      })
      .catch(err => console.error("Error fetching match data:", err));
  }, []);

  if (isLoadingAuth) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'sans-serif' }}>
        <h2>Loading Scouter...</h2>
      </div>
    );
  }

  if (showLogin && !user) {
    return (
      <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
        <button 
          onClick={() => setShowLogin(false)} 
          style={{ marginBottom: '20px', padding: '8px 16px', cursor: 'pointer' }}
        >
          ← Back to Dashboard
        </button>
        <LoginPage />
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        borderBottom: '2px solid #333', 
        paddingBottom: '15px',
        marginBottom: '30px' 
      }}>
        <h1 style={{ margin: 0 }}>Scouter v1.0</h1>
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <span>Logged in as: <strong>{user.username}</strong></span>
            <button onClick={logout} style={{ padding: '6px 12px', cursor: 'pointer' }}>Logout</button>
          </div>
        ) : (
          <button 
            onClick={() => setShowLogin(true)} 
            style={{ padding: '8px 16px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Login to Add Notes
          </button>
        )}
      </header>

      <main>
        <section>
          <div style={{ marginBottom: '20px' }}>
            <h2 style={{ marginBottom: '5px' }}>Match Schedule & Performances</h2>
            <p style={{ color: '#666', margin: 0 }}>Public data showing match status and alliance-based scoring.</p>
          </div>
          
          <table style={{ width: '100%', borderCollapse: 'collapse', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
            <thead>
              <tr style={{ backgroundColor: '#343a40', color: 'white', textAlign: 'left' }}>
                <th style={{ padding: '12px 15px' }}>Match / Team</th>
                <th style={{ padding: '12px 15px' }}>Type / Total Score</th>
                <th style={{ padding: '12px 15px' }}>Status / Auto</th>
                <th style={{ padding: '12px 15px' }}>Video / Endgame</th>
                {user && <th style={{ padding: '12px 15px' }}>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {scoutingData.length > 0 ? (
                scoutingData.map((match) => (
                  <React.Fragment key={match.match_id}>
                    {/* Main Match Header Row */}
                    <tr style={{ backgroundColor: '#f1f3f5', fontWeight: 'bold', borderTop: '2px solid #dee2e6' }}>
                      <td style={{ padding: '12px 15px' }}>Match {match.match_number}</td>
                      <td style={{ padding: '12px 15px', textTransform: 'capitalize' }}>{match.match_type}</td>
                      <td style={{ padding: '12px 15px', textTransform: 'capitalize' }}>{match.processing_status}</td>
                      <td style={{ padding: '12px 15px' }}>
                        {match.video_url ? (
                          <a href={match.video_url} target="_blank" rel="noreferrer" style={{ color: '#007bff' }}>Watch Video</a>
                        ) : 'No Video'}
                      </td>
                      {user && <td></td>}
                    </tr>

                    {/* Iterate through Alliances (Red/Blue) */}
                    {match.alliances && match.alliances.length > 0 ? (
                      match.alliances.map((alliance: any) => (
                        <React.Fragment key={alliance.alliance_id}>
                          {/* Alliance Identifier Row */}
                          <tr style={{ 
                            backgroundColor: alliance.color === 'red' ? '#fff5f5' : '#f0f7ff',
                            fontSize: '11px',
                            fontWeight: 'bold'
                          }}>
                            <td colSpan={user ? 5 : 4} style={{ padding: '5px 15px', color: alliance.color === 'red' ? '#c53030' : '#2b6cb0' }}>
                              {alliance.color.toUpperCase()} ALLIANCE
                            </td>
                          </tr>

                          {/* Iterate through Robot Performances inside this Alliance */}
                          {alliance.robot_performances?.map((perf: any) => (
                            <tr key={perf.performance_id || perf.perf_id} style={{ borderBottom: '1px solid #eee' }}>
                              <td style={{ padding: '10px 15px 10px 45px', color: '#495057', fontWeight: 600 }}>
                                Team {perf.team_id || perf.team_number}
                              </td>
                              <td style={{ padding: '10px 15px' }}>
                                <span style={{ color: '#28a745' }}>{perf.total_score || 0} pts</span>
                              </td>
                              <td style={{ padding: '10px 15px' }}>
                                {perf.auto_score || perf.auto_points || 0} auto
                              </td>
                              <td style={{ padding: '10px 15px' }}>
                                {perf.endgame_score || perf.climb_status || 0} endgame
                              </td>
                              {user && (
                                <td style={{ padding: '10px 15px' }}>
                                  <button style={{ fontSize: '12px', padding: '4px 8px', cursor: 'pointer' }}>
                                    Edit Note
                                  </button>
                                </td>
                              )}
                            </tr>
                          ))}
                        </React.Fragment>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={user ? 5 : 4} style={{ padding: '10px 15px 10px 45px', color: '#999', fontStyle: 'italic' }}>
                          No alliance or performance data available for this match.
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              ) : (
                <tr>
                  <td colSpan={user ? 5 : 4} style={{ padding: '50px', textAlign: 'center', color: '#666' }}>
                    <strong>No matches found.</strong>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}

export default App;