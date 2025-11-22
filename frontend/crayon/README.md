# Crayon Frontend Starter (replaces Streamlit)

This folder describes a minimal React + Crayon UI that talks to the FastAPI endpoints in `src/retention_reasoning/api.py`. It’s intended to replace the Streamlit stopgap with a production-ready React UI.

## Quickstart

```bash
cd frontend/crayon
npm init -y
npm install react react-dom @crayonai/react-core @crayonai/react-ui @crayonai/react-hooks @mantine/hooks axios
npm install -D typescript @types/react @types/react-dom vite
```

Add a `tsconfig.json` and `vite.config.ts` per standard Vite React setup.

Environment:
```
VITE_API_BASE=http://localhost:8000
```

## Example `src/App.tsx`

```tsx
import { useEffect, useState } from "react";
import { AgentLayout, MessageList, MessageInput } from "@crayonai/react-ui";
import { useStream } from "@crayonai/react-hooks";
import axios from "axios";

type Hypothesis = { cause: string; effect: string; validated: boolean };
type Campaign = { name: string; segment: any; offer: any; playbook: any; performance: any };

function App() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const { data: streamData, send } = useStream(); // optional if you wire SSE/WS

  const runAnalysis = async (payload: any) => {
    setLoading(true);
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_BASE || "http://localhost:8000"}/analyze`, payload);
      const { explanation, validated_causes, campaigns } = res.data;
      setCampaigns(campaigns || []);
      setMessages([
        ...messages,
        { role: "assistant", content: `Validated causes: ${validated_causes.join(", ")}` },
        { role: "assistant", content: explanation || "No explanation produced." },
      ]);
    } catch (err: any) {
      setMessages([...messages, { role: "assistant", content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (streamData) {
      setMessages((prev) => [...prev, { role: "assistant", content: streamData }]);
    }
  }, [streamData]);

  return (
    <AgentLayout
      sidebar={<div>Retention Reasoning Agent</div>}
      main={
        <>
          <MessageList messages={messages} />
          <MessageInput
            disabled={loading}
            placeholder="Paste opportunity JSON and press enter"
            onSend={(text) => {
              try {
                const payload = JSON.parse(text);
                runAnalysis(payload);
              } catch (e: any) {
                setMessages([...messages, { role: "assistant", content: `Invalid JSON: ${e.message}` }]);
              }
            }}
          />
          {campaigns.length > 0 && (
            <div>
              <h3>Campaigns</h3>
              {campaigns.map((c, i) => (
                <pre key={i}>{JSON.stringify(c, null, 2)}</pre>
              ))}
            </div>
          )}
        </>
      }
    />
  );
}

export default App;
```

## Backend hookup
- Run the FastAPI app: `uvicorn retention_reasoning.api:create_app --factory --reload`
- Ensure CORS is enabled (already configured) and `VITE_API_BASE` matches your backend URL.
- The `POST /analyze` endpoint returns validated causes, levers, explanation, and campaigns (segment/offer/playbook/performance).

## Notes
- Replace the simplistic rendering with Crayon primitives (cards, lists, graph visualizers) as needed.
- Wire streaming via SSE/WS if you want token-level updates; `useStream` hook from Crayon can be connected to the `/stream` endpoint (POST body supported in the FastAPI app).
- Remove or archive `examples/streamlit_app.py` once the React UI is in place.
