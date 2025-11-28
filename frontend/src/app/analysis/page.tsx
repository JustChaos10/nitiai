"use client";

import { useState } from "react";
import Link from "next/link";

// Types for the analysis response
interface Hypothesis {
  id: string;
  cause: string;
  effect: string;
  mechanism: string;
  validated: boolean;
  confidence?: number;
  p_value?: number;
  effect_size?: number;
  causal_structure?: {
    direct_effect: number;
    indirect_effect: number;
    total_effect: number;
    mediators: string[];
    actionable_lever: string;
  };
}

interface CausalGraph {
  nodes: string[];
  edges: Array<{
    from: string;
    to: string;
    strength: number;
    type: string;
  }>;
}

interface AnalysisResult {
  session_id: string;
  status: string;
  validated_causes: string[];
  recommended_levers: string[];
  explanation: string;
  hypotheses: Hypothesis[];
  causal_graph: CausalGraph;
  metrics?: Record<string, number>;
  insights?: Array<{ message: string; severity: string }>;
}

// Pipeline stations
const STATIONS = [
  { id: 1, name: "Hypothesis Generation", icon: "💡" },
  { id: 2, name: "Causal Testing", icon: "🔬" },
  { id: 3, name: "Confounder Analysis", icon: "🔍" },
  { id: 4, name: "Lever Estimation", icon: "⚖️" },
  { id: 5, name: "Explanation Generation", icon: "📝" },
];

export default function AnalysisPage() {
  const [loading, setLoading] = useState(false);
  const [currentStation, setCurrentStation] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state for custom opportunity
  const [useCustom, setUseCustom] = useState(false);
  const [formData, setFormData] = useState({
    type: "churn_spike",
    title: "",
    description: "",
    metric_name: "churn_rate_30d",
    baseline_value: 0.1,
    current_value: 0.15,
    sample_size: 1000,
    severity: "medium",
    cohort_description: "",
  });

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentStation(1);

    // Simulate station progression
    const stationInterval = setInterval(() => {
      setCurrentStation((prev) => (prev < 5 ? prev + 1 : prev));
    }, 2000);

    try {
      const endpoint = useCustom ? "/api/retention" : "/api/retention";
      const body = useCustom
        ? {
            action: "analyze",
            opportunity: {
              type: formData.type,
              title: formData.title || `Analysis of ${formData.metric_name}`,
              description: formData.description || "Custom analysis request",
              affected_cohort: { description: formData.cohort_description || "All customers" },
              metric_name: formData.metric_name,
              baseline_value: formData.baseline_value,
              current_value: formData.current_value,
              sample_size: formData.sample_size,
              severity: formData.severity,
            },
          }
        : { action: "analyze" };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      clearInterval(stationInterval);
      setCurrentStation(5);

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      clearInterval(stationInterval);
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#ededed]">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-semibold">Retention Reasoning Agent</h1>
          <nav className="flex gap-4">
            <Link href="/" className="text-gray-400 hover:text-white transition">
              Chat
            </Link>
            <Link href="/analysis" className="text-white font-medium">
              Analysis
            </Link>
          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Pipeline Visualization */}
        <div className="mb-8">
          <h2 className="text-lg font-medium mb-4">Analysis Pipeline</h2>
          <div className="flex items-center justify-between bg-gray-900 rounded-lg p-4">
            {STATIONS.map((station, idx) => (
              <div key={station.id} className="flex items-center">
                <div
                  className={`flex flex-col items-center ${
                    currentStation >= station.id
                      ? "text-green-400"
                      : "text-gray-500"
                  }`}
                >
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl ${
                      currentStation >= station.id
                        ? "bg-green-900/50"
                        : "bg-gray-800"
                    } ${currentStation === station.id && loading ? "animate-pulse" : ""}`}
                  >
                    {station.icon}
                  </div>
                  <span className="text-xs mt-2 text-center max-w-[80px]">
                    {station.name}
                  </span>
                </div>
                {idx < STATIONS.length - 1 && (
                  <div
                    className={`w-12 h-0.5 mx-2 ${
                      currentStation > station.id ? "bg-green-400" : "bg-gray-700"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2 bg-gray-900 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium">Analysis Configuration</h2>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={useCustom}
                  onChange={(e) => setUseCustom(e.target.checked)}
                  className="rounded"
                />
                Custom Opportunity
              </label>
            </div>

            {useCustom ? (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Type</label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                    className="w-full bg-gray-800 rounded px-3 py-2 text-sm"
                  >
                    <option value="churn_spike">Churn Spike</option>
                    <option value="repeat_rate_drop">Repeat Rate Drop</option>
                    <option value="ltv_decline">LTV Decline</option>
                    <option value="engagement_drop">Engagement Drop</option>
                    <option value="cohort_anomaly">Cohort Anomaly</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Metric</label>
                  <input
                    type="text"
                    value={formData.metric_name}
                    onChange={(e) => setFormData({ ...formData, metric_name: e.target.value })}
                    className="w-full bg-gray-800 rounded px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Baseline Value</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.baseline_value}
                    onChange={(e) => setFormData({ ...formData, baseline_value: parseFloat(e.target.value) })}
                    className="w-full bg-gray-800 rounded px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Current Value</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.current_value}
                    onChange={(e) => setFormData({ ...formData, current_value: parseFloat(e.target.value) })}
                    className="w-full bg-gray-800 rounded px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Sample Size</label>
                  <input
                    type="number"
                    value={formData.sample_size}
                    onChange={(e) => setFormData({ ...formData, sample_size: parseInt(e.target.value) })}
                    className="w-full bg-gray-800 rounded px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Severity</label>
                  <select
                    value={formData.severity}
                    onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                    className="w-full bg-gray-800 rounded px-3 py-2 text-sm"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="block text-sm text-gray-400 mb-1">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full bg-gray-800 rounded px-3 py-2 text-sm"
                    rows={2}
                    placeholder="Describe the retention issue..."
                  />
                </div>
              </div>
            ) : (
              <p className="text-gray-400 text-sm">
                Run analysis on the loaded dataset using automatic opportunity detection.
                The system will analyze current metrics and identify retention issues.
              </p>
            )}

            <button
              onClick={runAnalysis}
              disabled={loading}
              className={`mt-4 px-6 py-2 rounded font-medium transition ${
                loading
                  ? "bg-gray-700 text-gray-400 cursor-not-allowed"
                  : "bg-green-600 hover:bg-green-500 text-white"
              }`}
            >
              {loading ? "Analyzing..." : "Run Analysis"}
            </button>
          </div>

          {/* Quick Stats */}
          <div className="bg-gray-900 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4">Quick Stats</h2>
            {result?.metrics ? (
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Churn Rate</span>
                  <span>{((result.metrics.churn_rate_30d || 0) * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Repeat Rate</span>
                  <span>{((result.metrics.repeat_purchase_rate || 0) * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Avg Order Value</span>
                  <span>${(result.metrics.avg_order_value || 0).toFixed(2)}</span>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">Run analysis to see metrics</p>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-900/30 border border-red-800 rounded-lg p-4">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Explanation */}
            <div className="bg-gray-900 rounded-lg p-6">
              <h2 className="text-lg font-medium mb-4">Analysis Summary</h2>
              <p className="text-gray-300 whitespace-pre-wrap">
                {result.explanation || "Analysis completed successfully."}
              </p>
            </div>

            {/* Validated Causes & Levers */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-900 rounded-lg p-6">
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                  <span className="text-green-400">✓</span> Validated Causes
                </h2>
                {result.validated_causes?.length > 0 ? (
                  <ul className="space-y-2">
                    {result.validated_causes.map((cause, idx) => (
                      <li key={idx} className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-green-400 rounded-full" />
                        <span>{cause}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500">No validated causes found</p>
                )}
              </div>

              <div className="bg-gray-900 rounded-lg p-6">
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                  <span className="text-blue-400">⚡</span> Recommended Levers
                </h2>
                {result.recommended_levers?.length > 0 ? (
                  <ul className="space-y-2">
                    {result.recommended_levers.map((lever, idx) => (
                      <li key={idx} className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-blue-400 rounded-full" />
                        <span>{lever}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500">No levers recommended</p>
                )}
              </div>
            </div>

            {/* Hypotheses */}
            <div className="bg-gray-900 rounded-lg p-6">
              <h2 className="text-lg font-medium mb-4">Hypotheses</h2>
              <div className="space-y-4">
                {result.hypotheses?.map((hyp) => (
                  <div
                    key={hyp.id}
                    className={`border rounded-lg p-4 ${
                      hyp.validated
                        ? "border-green-800 bg-green-900/20"
                        : "border-gray-700 bg-gray-800/50"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${
                              hyp.validated
                                ? "bg-green-800 text-green-200"
                                : "bg-gray-700 text-gray-300"
                            }`}
                          >
                            {hyp.validated ? "Validated" : "Not Validated"}
                          </span>
                          <span className="text-sm text-gray-400">{hyp.id}</span>
                        </div>
                        <h3 className="font-medium">
                          {hyp.cause} → {hyp.effect}
                        </h3>
                        <p className="text-gray-400 text-sm mt-1">{hyp.mechanism}</p>
                      </div>
                      {hyp.validated && (
                        <div className="text-right text-sm">
                          <div className="text-gray-400">
                            Confidence: <span className="text-white">{((hyp.confidence || 0) * 100).toFixed(0)}%</span>
                          </div>
                          <div className="text-gray-400">
                            Effect Size: <span className="text-white">{(hyp.effect_size || 0).toFixed(3)}</span>
                          </div>
                        </div>
                      )}
                    </div>
                    {hyp.causal_structure && (
                      <div className="mt-3 pt-3 border-t border-gray-700 text-sm">
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <span className="text-gray-400">Direct Effect:</span>{" "}
                            {hyp.causal_structure.direct_effect.toFixed(3)}
                          </div>
                          <div>
                            <span className="text-gray-400">Indirect Effect:</span>{" "}
                            {hyp.causal_structure.indirect_effect.toFixed(3)}
                          </div>
                          <div>
                            <span className="text-gray-400">Total Effect:</span>{" "}
                            {hyp.causal_structure.total_effect.toFixed(3)}
                          </div>
                        </div>
                        {hyp.causal_structure.actionable_lever && (
                          <div className="mt-2">
                            <span className="text-gray-400">Actionable Lever:</span>{" "}
                            <span className="text-blue-400">{hyp.causal_structure.actionable_lever}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Causal Graph */}
            {result.causal_graph?.nodes?.length > 0 && (
              <div className="bg-gray-900 rounded-lg p-6">
                <h2 className="text-lg font-medium mb-4">Causal Graph</h2>
                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="flex flex-wrap gap-2 mb-4">
                    {result.causal_graph.nodes.map((node) => (
                      <span
                        key={node}
                        className="px-3 py-1 bg-gray-700 rounded-full text-sm"
                      >
                        {node}
                      </span>
                    ))}
                  </div>
                  <div className="space-y-2">
                    {result.causal_graph.edges.map((edge, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <span className="text-gray-300">{edge.from}</span>
                        <span className="text-gray-500">→</span>
                        <span className="text-gray-300">{edge.to}</span>
                        <span className="text-gray-500 ml-2">
                          (strength: {edge.strength.toFixed(2)}, {edge.type})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

