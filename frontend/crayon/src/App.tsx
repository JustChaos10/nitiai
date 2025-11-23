import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { ReasoningGraph } from "./components/ReasoningGraph";
import { HypothesisExplorer } from "./components/HypothesisExplorer";
import "./App.css";

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

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  template?: "analysis_result" | "hypotheses" | "causal_graph";
  data?: any;
};

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const defaultPayload = {
  opportunity: {
    type: "churn_spike",
    title: "High churn in recent cohort",
    description: "Recent customers show elevated churn rates",
    affected_cohort: {
      description: "All customers",
    },
    metric_name: "churn_30d",
    baseline_value: 0.15,
    current_value: 0.18,
    sample_size: 500,
    severity: "high",
    business_context: {
      recent_changes: "Warehouse delays",
    },
  },
  data_preview: null,
  business_context: "Recent shipping delays",
};

function AnalysisResultComponent({ data }: { data: any }) {
  return (
    <div style={{ padding: "16px", backgroundColor: "#f8fafc", borderRadius: "8px", marginTop: "12px" }}>
      <h3 style={{ margin: "0 0 12px 0", fontSize: "16px", fontWeight: 600 }}>Analysis Results</h3>
      
      {data.validated_causes && data.validated_causes.length > 0 && (
        <div style={{ marginBottom: "12px" }}>
          <strong>Validated Causes:</strong>
          <div style={{ marginTop: "4px" }}>
            {data.validated_causes.map((cause: string) => (
              <span key={cause} style={{ display: "inline-block", padding: "4px 8px", backgroundColor: "#d1fae5", color: "#065f46", borderRadius: "4px", marginRight: "8px", marginTop: "4px", fontSize: "12px" }}>
                {cause}
              </span>
            ))}
          </div>
        </div>
      )}

      {data.explanation && (
        <div style={{ marginBottom: "12px" }}>
          <strong>Explanation:</strong>
          <p style={{ margin: "4px 0 0 0", fontSize: "14px", color: "#475569" }}>{data.explanation}</p>
        </div>
      )}

      {data.hypotheses && data.hypotheses.length > 0 && (
        <div>
          <strong>Hypotheses Generated: {data.hypotheses.length}</strong>
          <div style={{ marginTop: "8px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
            {data.hypotheses.slice(0, 4).map((h: Hypothesis) => (
              <div key={h.id} style={{ padding: "8px", backgroundColor: "white", borderRadius: "4px", borderLeft: `3px solid ${h.validated ? "#10b981" : "#ef4444"}` }}>
                <div style={{ fontSize: "12px", fontWeight: 600 }}>{h.cause} → {h.effect}</div>
                <div style={{ fontSize: "11px", color: "#64748b" }}>{h.validated ? "✓ Validated" : "✗ Not validated"}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function HypothesesComponent({ data }: { data: Hypothesis[] }) {
  return (
    <div style={{ marginTop: "12px" }}>
      <HypothesisExplorer hypotheses={data} onHypothesisSelect={(h) => console.log("Selected:", h)} />
    </div>
  );
}

function GraphComponent({ data }: { data: CausalGraph }) {
  return (
    <div style={{ marginTop: "12px" }}>
      <ReasoningGraph graph={data} onNodeClick={(nodeId) => console.log("Clicked node:", nodeId)} />
    </div>
  );
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Welcome to the Retention Reasoning Agent. Paste an opportunity JSON to analyze retention causes.",
    },
  ]);
  const [inputValue, setInputValue] = useState(JSON.stringify(defaultPayload, null, 2));
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue,
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const payload = JSON.parse(inputValue);
      const res = await axios.post(`${API_BASE}/analyze`, payload);
      const { explanation, validated_causes, hypotheses, causal_graph } = res.data;

      // Add analysis results message
      const analysisMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Analysis complete",
        template: "analysis_result",
        data: {
          validated_causes,
          explanation,
          hypotheses,
          causal_graph,
        },
      };
      setMessages((prev) => [...prev, analysisMessage]);

      // Add hypotheses message if available
      if (hypotheses && hypotheses.length > 0) {
        const hypothesesMessage: Message = {
          id: (Date.now() + 2).toString(),
          role: "assistant",
          content: `Found ${hypotheses.length} hypotheses to explore`,
          template: "hypotheses",
          data: hypotheses,
        };
        setMessages((prev) => [...prev, hypothesesMessage]);
      }

      // Add graph message if available
      if (causal_graph) {
        const graphMessage: Message = {
          id: (Date.now() + 3).toString(),
          role: "assistant",
          content: "Causal structure identified",
          template: "causal_graph",
          data: causal_graph,
        };
        setMessages((prev) => [...prev, graphMessage]);
      }

      // Clear input and reset
      setInputValue(JSON.stringify(defaultPayload, null, 2));
    } catch (err: any) {
      let errorContent = err.message;
      if (err.response?.data?.detail) {
        errorContent = typeof err.response.data.detail === 'string' 
          ? err.response.data.detail 
          : JSON.stringify(err.response.data.detail, null, 2);
      }

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${errorContent}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === "Enter") {
      handleSendMessage();
    }
  };

  return (
    <div className="crayon-app">
      <div className="crayon-header">
        <h1>Retention Reasoning Agent</h1>
        <p>Powered by Causal Inference & LLM-Generated Hypotheses</p>
      </div>

      <div className="crayon-container">
        <div className="crayon-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`message-wrapper ${msg.role}`}>
              <div className={`message-bubble ${msg.role}`}>
                {msg.role === "assistant" && <div className="assistant-avatar">🤖</div>}
                
                <div className="message-content">
                  <p>{msg.content}</p>

                  {msg.template === "analysis_result" && msg.data && (
                    <AnalysisResultComponent data={msg.data} />
                  )}

                  {msg.template === "hypotheses" && msg.data && (
                    <HypothesesComponent data={msg.data} />
                  )}

                  {msg.template === "causal_graph" && msg.data && (
                    <GraphComponent data={msg.data} />
                  )}
                </div>

                {msg.role === "user" && <div className="user-avatar">👤</div>}
              </div>
            </div>
          ))}
          {loading && (
            <div className="message-wrapper assistant">
              <div className="message-bubble assistant">
                <div className="assistant-avatar">🤖</div>
                <div className="message-content">
                  <p className="loading-text">Analyzing...</p>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="crayon-input-area">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            className="crayon-input"
            placeholder="Paste opportunity JSON here... (Ctrl+Enter to send)"
            rows={6}
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !inputValue.trim()}
            className="crayon-send-btn"
          >
            {loading ? "Analyzing..." : "Analyze"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
