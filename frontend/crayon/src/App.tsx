import { useEffect, useState } from "react";
import axios from "axios";
import { AgentLayout, MessageList, MessageInput } from "@crayonai/react-ui";
import "@crayonai/react-ui/dist/style.css";
import { ReasoningGraph } from "./components/ReasoningGraph";
import { HypothesisExplorer } from "./components/HypothesisExplorer";

type Hypothesis = {
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
};

type CausalGraph = {
  nodes: string[];
  edges: Array<{
    from: string;
    to: string;
    strength: number;
    type: "direct" | "indirect" | "confounder";
  }>;
};

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const defaultPayload = {
  opportunity: {
    title: "High churn in recent cohort",
    description: "Recent customers show elevated churn rates",
    metric_name: "churn_30d",
    baseline_value: 0.15,
    current_value: 0.18,
    sample_size: 500,
    severity: "high",
    type: "churn_spike",
    cohort: { description: "All customers" },
    business_context: { recent_changes: "Warehouse delays" },
  },
  data_preview: null,
  business_context: "Recent shipping delays",
};

function App() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [causalGraph, setCausalGraph] = useState<CausalGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"chat" | "hypotheses" | "graph">("chat");

  const runAnalysis = async (payloadText: string) => {
    setLoading(true);
    try {
      const payload = JSON.parse(payloadText);
      const res = await axios.post(`${API_BASE}/analyze`, payload);
      const { explanation, validated_causes, hypotheses, causal_graph } = res.data;

      setHypotheses(hypotheses || []);
      setCausalGraph(causal_graph || null);

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Validated causes: ${validated_causes?.join(", ") || "none"}` },
        { role: "assistant", content: explanation || "No explanation produced." },
      ]);

      // Auto-switch to hypotheses tab if we have results
      if (hypotheses && hypotheses.length > 0) {
        setActiveTab("hypotheses");
      }
    } catch (err: any) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setMessages([{ role: "assistant", content: "Paste an opportunity JSON and press enter to analyze." }]);
  }, []);

  return (
    <AgentLayout
      sidebar={
        <div style={{ padding: 12 }}>
          <h3>Retention Reasoning Agent</h3>
          <p style={{ fontSize: 12, color: "#64748b" }}>Backend: {API_BASE}</p>
          <hr style={{ margin: "12px 0", border: "none", borderTop: "1px solid #e2e8f0" }} />
          <div style={{ fontSize: 12 }}>
            <div style={{ marginBottom: 8 }}>
              <strong>Hypotheses:</strong> {hypotheses.length}
            </div>
            <div>
              <strong>Validated:</strong> {hypotheses.filter((h) => h.validated).length}
            </div>
          </div>
        </div>
      }
      main={
        <>
          {/* Tab Navigation */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "16px", borderBottom: "1px solid #e2e8f0" }}>
            <button
              onClick={() => setActiveTab("chat")}
              style={{
                padding: "8px 16px",
                border: "none",
                background: activeTab === "chat" ? "#3b82f6" : "transparent",
                color: activeTab === "chat" ? "white" : "#64748b",
                cursor: "pointer",
                borderRadius: "4px 4px 0 0",
                fontWeight: activeTab === "chat" ? 600 : 400,
              }}
            >
              Chat
            </button>
            <button
              onClick={() => setActiveTab("hypotheses")}
              style={{
                padding: "8px 16px",
                border: "none",
                background: activeTab === "hypotheses" ? "#3b82f6" : "transparent",
                color: activeTab === "hypotheses" ? "white" : "#64748b",
                cursor: "pointer",
                borderRadius: "4px 4px 0 0",
                fontWeight: activeTab === "hypotheses" ? 600 : 400,
              }}
            >
              Hypotheses ({hypotheses.length})
            </button>
            <button
              onClick={() => setActiveTab("graph")}
              style={{
                padding: "8px 16px",
                border: "none",
                background: activeTab === "graph" ? "#3b82f6" : "transparent",
                color: activeTab === "graph" ? "white" : "#64748b",
                cursor: "pointer",
                borderRadius: "4px 4px 0 0",
                fontWeight: activeTab === "graph" ? 600 : 400,
              }}
              disabled={!causalGraph}
            >
              Causal Graph
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === "chat" && (
            <>
              <MessageList messages={messages} />
              <MessageInput
                disabled={loading}
                placeholder="Paste opportunity JSON"
                initialValue={JSON.stringify(defaultPayload, null, 2)}
                onSend={(text) => runAnalysis(text)}
              />
            </>
          )}

          {activeTab === "hypotheses" && (
            <div style={{ height: "600px" }}>
              {hypotheses.length > 0 ? (
                <HypothesisExplorer
                  hypotheses={hypotheses}
                  onHypothesisSelect={(h) => console.log("Selected:", h)}
                />
              ) : (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    height: "100%",
                    color: "#94a3b8",
                  }}
                >
                  No hypotheses available. Run an analysis first.
                </div>
              )}
            </div>
          )}

          {activeTab === "graph" && (
            <div>
              {causalGraph ? (
                <ReasoningGraph
                  graph={causalGraph}
                  onNodeClick={(nodeId) => console.log("Clicked node:", nodeId)}
                />
              ) : (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    height: "400px",
                    color: "#94a3b8",
                  }}
                >
                  No causal graph available. Run an analysis first.
                </div>
              )}
            </div>
          )}
        </>
      }
    />
  );
}

export default App;
