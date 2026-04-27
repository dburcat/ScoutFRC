import { useState } from 'react';
import { ArrowLeft, X, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';

interface Alliance {
  id: string;
  name: string;
  teams: number[];
}

export default function AllianceBuilderPage() {
  const navigate = useNavigate();
  const [red, setRed] = useState<number[]>([]);
  const [blue, setBlue] = useState<number[]>([]);
  const [allianceName, setAllianceName] = useState('');
  const [saved, setSaved] = useState(false);

  const handleAddTeam = (color: 'red' | 'blue', teamNum: number) => {
    const arr = color === 'red' ? red : blue;
    if (arr.length < 3 && !arr.includes(teamNum)) {
      if (color === 'red') setRed([...arr, teamNum]);
      else setBlue([...arr, teamNum]);
    }
  };

  const handleRemoveTeam = (color: 'red' | 'blue', idx: number) => {
    const arr = color === 'red' ? red : blue;
    if (color === 'red') setRed(arr.filter((_, i) => i !== idx));
    else setBlue(arr.filter((_, i) => i !== idx));
  };

  const handleSave = async () => {
    if (red.length === 0 || blue.length === 0) {
      alert('Please select at least one team for each alliance');
      return;
    }
    
    // TODO: POST to /alliances endpoint
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const avgScore = (teams: number[]) => {
    if (teams.length === 0) return '—';
    // TODO: Calculate from team average scores
    return Math.round(Math.random() * 100); // Placeholder
  };

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Header */}
      <div className="px-6 py-3.5 border-b border-app-border flex-shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="text-slate-500 hover:text-slate-300 transition-colors p-1"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <p className="text-[15px] font-medium text-white">Alliance Builder</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Plan your strategy</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={red.length === 0 || blue.length === 0}
          className="px-4 py-1.5 bg-brand text-white text-xs font-medium rounded-lg hover:bg-brand/85 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saved ? '✓ Saved' : 'Save Alliance'}
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {/* Alliance name */}
          <div className="mb-6">
            <label className="text-[11px] font-medium text-slate-600 block mb-2">
              Alliance name (optional)
            </label>
            <input
              type="text"
              value={allianceName}
              onChange={e => setAllianceName(e.target.value)}
              placeholder="e.g. Red Power Play"
              className="w-full px-3 py-2 bg-app-card border border-app-border rounded-lg text-white placeholder:text-slate-600 text-sm"
            />
          </div>

          {/* Alliances */}
          <div className="grid grid-cols-2 gap-5">
            {(['red', 'blue'] as const).map(color => (
              <div
                key={color}
                className={clsx(
                  'bg-app-card border rounded-lg p-5',
                  color === 'red' ? 'border-red-500/20' : 'border-blue-500/20'
                )}
              >
                <div className="mb-4">
                  <h3 className={clsx('text-sm font-medium capitalize mb-1', {
                    'text-red-400': color === 'red',
                    'text-blue-400': color === 'blue',
                  })}>
                    {color} Alliance
                  </h3>
                  <p className="text-xs text-slate-600">{color === 'red' ? red : blue}.length/3 teams</p>
                </div>

                {/* Selected teams */}
                <div className="space-y-2 mb-4">
                  {(color === 'red' ? red : blue).map((teamNum, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between px-3 py-2 bg-app-muted rounded-lg"
                    >
                      <span className="font-mono text-white font-medium">Team {teamNum}</span>
                      <button
                        onClick={() => handleRemoveTeam(color, idx)}
                        className="text-slate-500 hover:text-red-400 transition-colors p-0.5"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Projected score */}
                <div className="mb-4 p-3 bg-app-muted rounded-lg">
                  <p className="text-[10px] text-slate-600 mb-1">Projected score</p>
                  <p className="text-xl font-bold text-white">{avgScore(color === 'red' ? red : blue)}</p>
                </div>

                {/* Add team button */}
                {(color === 'red' ? red : blue).length < 3 && (
                  <button
                    onClick={() => {
                      const teamNum = parseInt(prompt('Enter team number:') || '');
                      if (!isNaN(teamNum)) handleAddTeam(color, teamNum);
                    }}
                    className="w-full px-3 py-2 border border-app-border rounded-lg text-slate-400 hover:text-slate-200 hover:border-app-muted transition-colors text-xs font-medium flex items-center justify-center gap-1"
                  >
                    <Plus size={12} />
                    Add team
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Info */}
          <div className="mt-8 p-4 bg-app-card border border-app-border rounded-lg">
            <p className="text-[11px] text-slate-600">
              💡 <span className="font-medium">Tip:</span> Select up to 3 teams per alliance. Projected scores are based on average match performance.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
