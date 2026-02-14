
import React, { useState, useRef } from 'react';
import { analyzeRoadSafetyVideo } from './services/gemini';
import { HazardDetection } from './types';
import { 
  AlertTriangle, 
  Upload, 
  ShieldCheck, 
  Download,
  Video,
  Info,
  ChevronRight,
  Loader2,
  Clock,
  Eye,
  Navigation,
  CheckCircle2,
  FileJson
} from 'lucide-react';

const App: React.FC = () => {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [hazards, setHazards] = useState<HazardDetection[] | null>(null);
  const [rawJson, setRawJson] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const MAX_FILE_SIZE = 100 * 1024 * 1024;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > MAX_FILE_SIZE) {
        setError(`File size too large (${(file.size / (1024 * 1024)).toFixed(1)}MB). Please use a video under 100MB.`);
        return;
      }
      setVideoFile(file);
      setVideoUrl(URL.createObjectURL(file));
      setHazards(null);
      setRawJson(null);
      setError(null);
    }
  };

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve((reader.result as string).split(',')[1]);
      reader.onerror = (error) => reject(error);
    });
  };

  const handleAnalyze = async () => {
    if (!videoFile) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      const base64 = await fileToBase64(videoFile);
      const jsonResponse = await analyzeRoadSafetyVideo(base64, videoFile.type);
      setRawJson(jsonResponse);
      setHazards(JSON.parse(jsonResponse));
    } catch (err: any) {
      setError(err.message || "An error occurred during analysis.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const downloadJson = () => {
    if (!rawJson) return;
    const blob = new Blob([rawJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `roadsense-analysis-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getSeverityColor = (severity: number) => {
    if (severity >= 4) return 'bg-red-500 text-white';
    if (severity >= 3) return 'bg-orange-500 text-white';
    return 'bg-yellow-500 text-slate-950';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 md:py-12">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-red-600 rounded-2xl shadow-lg shadow-red-900/20">
            <ShieldCheck className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white">RoadSense <span className="text-red-500">AI</span></h1>
            <p className="text-slate-400 font-medium">Expert Indian Road Hazard Detection</p>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-slate-900 p-1 rounded-full border border-slate-800">
           <div className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-300">
             <CheckCircle2 className="w-4 h-4 text-green-500" />
             GoPro Dashcam Ready
           </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-red-500" /> 
              Dashcam Footage
            </h2>
            <label className="group relative flex flex-col items-center justify-center w-full h-64 border-2 border-dashed border-slate-700 rounded-2xl cursor-pointer bg-slate-950/50 hover:bg-slate-950 hover:border-red-500/50 transition-all">
              <div className="flex flex-col items-center justify-center text-center px-4">
                <Video className="w-12 h-12 text-slate-500 mb-4 group-hover:text-red-500 transition-colors" />
                <p className="mb-2 text-sm text-slate-400 font-medium">Click to upload footage</p>
                <p className="text-xs text-slate-500">Windshield-mounted, forward-facing</p>
              </div>
              <input type="file" className="hidden" accept="video/*" onChange={handleFileChange} />
            </label>

            {videoUrl && (
              <div className="mt-6 space-y-3">
                <div className="rounded-xl overflow-hidden border border-slate-800 bg-black shadow-inner">
                  <video ref={videoRef} src={videoUrl} controls className="w-full aspect-video" />
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-800/30 p-2 rounded-lg">
                  <Info className="w-4 h-4 text-blue-400" />
                  File: {(videoFile!.size / (1024 * 1024)).toFixed(1)}MB
                </div>
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!videoFile || isAnalyzing}
              className={`mt-6 w-full py-4 px-6 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all ${
                isAnalyzing || !videoFile
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-500 text-white shadow-lg active:scale-[0.98]'
              }`}
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Scanning Frame-by-Frame...
                </>
              ) : (
                <>
                  <Eye className="w-5 h-5" />
                  Start Detection
                </>
              )}
            </button>
            {error && (
              <div className="mt-4 p-4 bg-red-900/20 border border-red-500/50 rounded-xl text-red-400 text-sm flex gap-3">
                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                {error}
              </div>
            )}
          </div>

          <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Hazard Classes</h3>
            <div className="grid grid-cols-2 gap-2">
              {['POTHOLE', 'SPEED_BREAKER', 'PEDESTRIAN_ZONE', 'OVERHEAD_OBSTRUCTION', 'ROAD_WORK', 'SHARP_CURVE', 'SURFACE_CHANGE'].map((cls) => (
                <div key={cls} className="text-[10px] px-2 py-1 bg-slate-800 rounded border border-slate-700 text-slate-400 font-mono truncate">
                  {cls}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="lg:col-span-7">
          {!hazards && !isAnalyzing ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-12 border border-slate-800 border-dashed rounded-3xl bg-slate-900/10">
              <div className="w-20 h-20 bg-slate-800/30 rounded-full flex items-center justify-center mb-6">
                <Navigation className="w-10 h-10 text-slate-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-300 mb-2">Detection Pipeline Idle</h3>
              <p className="text-slate-500 max-w-xs text-sm">Upload dashcam footage to begin autonomous hazard extraction.</p>
            </div>
          ) : isAnalyzing ? (
            <div className="h-full flex flex-col items-center justify-center p-12 bg-slate-900/80 border border-slate-800 rounded-3xl">
              <div className="relative w-32 h-32 mb-10">
                 <div className="absolute inset-0 border-4 border-red-500/10 rounded-full"></div>
                 <div className="absolute inset-0 border-4 border-red-500 border-t-transparent rounded-full animate-spin"></div>
                 <div className="absolute inset-0 flex items-center justify-center text-red-500">
                    <Video className="w-12 h-12" />
                 </div>
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">RoadSense Processing</h3>
              <p className="text-slate-400 text-center max-w-sm mb-6">Analyzing Indian road dynamics. Large clips may take a moment to synchronize results.</p>
              <div className="w-full max-w-xs bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div className="bg-red-500 h-full animate-[progress_2s_ease-in-out_infinite]" style={{ width: '40%' }}></div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl flex flex-col h-[700px]">
                <div className="p-6 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-slate-900 z-10">
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-semibold text-white">Extracted Hazards</h2>
                    <span className="bg-slate-800 text-slate-300 text-[10px] font-bold px-2 py-0.5 rounded-full border border-slate-700">
                      {hazards?.length || 0} DETECTED
                    </span>
                  </div>
                  <button 
                    onClick={downloadJson}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold rounded-xl border border-slate-700 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Download JSON
                  </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
                  {hazards && hazards.length > 0 ? (
                    hazards.map((hazard) => (
                      <div key={hazard.hazard_id} className="bg-slate-950 border border-slate-800 rounded-2xl p-5 hover:border-red-500/50 transition-all group">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <div className={`px-2 py-1 rounded text-[10px] font-black tracking-tighter ${getSeverityColor(hazard.severity)}`}>
                              SEV {hazard.severity}
                            </div>
                            <span className="text-slate-100 font-bold text-sm tracking-tight">{hazard.category.replace('_', ' ')}</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
                            <Clock className="w-3 h-3" />
                            {hazard.timestamp_offset_sec.toFixed(1)}s
                          </div>
                        </div>
                        
                        <p className="text-slate-300 text-sm leading-relaxed mb-4">{hazard.description}</p>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div className="p-3 bg-slate-900 rounded-xl border border-slate-800/50">
                            <span className="text-[10px] text-slate-500 font-bold block mb-1">RECOMMENDED ACTION</span>
                            <span className="text-xs text-slate-300 font-medium">{hazard.driver_action}</span>
                          </div>
                          <div className="p-3 bg-slate-900 rounded-xl border border-slate-800/50">
                            <span className="text-[10px] text-slate-500 font-bold block mb-1">COORD. (BBOX)</span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              [{hazard.bounding_box.x_min.toFixed(2)}, {hazard.bounding_box.y_min.toFixed(2)}] to [{hazard.bounding_box.x_max.toFixed(2)}, {hazard.bounding_box.y_max.toFixed(2)}]
                            </span>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 italic text-sm">
                      No hazards detected in this segment.
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileJson className="w-6 h-6 text-blue-500" />
                  <div>
                    <h3 className="text-sm font-bold text-white">Full Structured Output</h3>
                    <p className="text-xs text-slate-500">Access the raw JSON data for backend integration.</p>
                  </div>
                </div>
                <button 
                  onClick={downloadJson}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-xl transition-colors shadow-lg shadow-blue-900/20"
                >
                  Export Data
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      <footer className="mt-16 pt-8 border-t border-slate-900 text-center">
        <p className="text-slate-600 text-sm font-medium">RoadSense Core v2.4 • Gemini AI Engine • GoPro Optic Profile</p>
      </footer>

      <style>{`
        @keyframes progress {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(250%); }
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #1e293b;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #334155;
        }
      `}</style>
    </div>
  );
};

export default App;
