import { useEffect, useState } from "react";
import axios from "axios";
import { AgentLayout, MessageList, MessageInput } from "@crayonai/react-ui";
import "@crayonai/react-ui/dist/style.css";

type Campaign = {
  name: string;
  segment: any;
  offer: any;
  playbook: any;
  performance: any;
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
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(false);

  const runAnalysis = async (payloadText: string) => {
    setLoading(true);
    try {
      const payload = JSON.parse(payloadText);
      const res = await axios.post(`${API_BASE}/analyze`, payload);
      const { explanation, validated_causes, campaigns } = res.data;
      setCampaigns(campaigns || []);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Validated causes: ${validated_causes?.join(", ") || "none"}` },
        { role: "assistant", content: explanation || "No explanation produced." },
      ]);
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
          <p>Backend: FastAPI at {API_BASE}</p>
        </div>
      }
      main={
        <>
          <MessageList messages={messages} />
          <MessageInput
            disabled={loading}
            placeholder="Paste opportunity JSON"
            initialValue={JSON.stringify(defaultPayload, null, 2)}
            onSend={(text) => runAnalysis(text)}
          />
          {campaigns.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h3>Campaigns</h3>
              {campaigns.map((c, i) => (
                <details key={i} style={{ marginBottom: 8 }}>
                  <summary>{c.name}</summary>
                  <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(c, null, 2)}</pre>
                </details>
              ))}
            </div>
          )}
        </>
      }
    />
  );
}

export default App;
