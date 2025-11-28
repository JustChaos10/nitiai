import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import { transformStream } from "@crayonai/stream";
import { DBMessage, getMessageStore } from "./messageStore";

// Python backend URL - configurable via environment variable
const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

// Cache for LangGraph analysis results (per thread)
const analysisCache: Map<string, { result: CausalAnalysisResult; timestamp: number }> = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

// Types for LangGraph causal analysis results
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

interface CausalAnalysisResult {
  session_id: string;
  status: string;
  validated_causes: string[];
  recommended_levers: string[];
  explanation: string;
  hypotheses: Hypothesis[];
  causal_graph: {
    nodes: string[];
    edges: Array<{ from: string; to: string; strength: number; type: string }>;
  };
}

// Run LangGraph causal analysis via Python backend
async function runCausalAnalysis(brandId?: string): Promise<CausalAnalysisResult | null> {
  try {
    console.log("Running LangGraph causal analysis...");
    
    const response = await fetch(`${PYTHON_API_URL}/analyze/from-data`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        brand_id: brandId,
        metric_name: "churn_flag",
      }),
    });

    if (!response.ok) {
      console.warn("LangGraph analysis failed:", response.status);
      return null;
    }

    const result = await response.json();
    console.log("LangGraph analysis complete:", result.session_id);
    return result as CausalAnalysisResult;
  } catch (error) {
    console.warn("Error running causal analysis:", error);
    return null;
  }
}

// Get cached analysis or run new one
async function getCausalAnalysis(threadId: string, brandId?: string): Promise<CausalAnalysisResult | null> {
  const cacheKey = `${threadId}-${brandId || "all"}`;
  const cached = analysisCache.get(cacheKey);
  
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    console.log("Using cached LangGraph analysis");
    return cached.result;
  }
  
  const result = await runCausalAnalysis(brandId);
  if (result) {
    analysisCache.set(cacheKey, { result, timestamp: Date.now() });
  }
  return result;
}

// Fetch basic retention context from Python backend
async function getRetentionContext(brandId?: string): Promise<{ context: string; metrics: Record<string, number> }> {
  try {
    const response = await fetch(`${PYTHON_API_URL}/chat/context`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "",
        brand_id: brandId,
      }),
    });

    if (!response.ok) {
      console.warn("Failed to fetch retention context, using fallback");
      return { context: "", metrics: {} };
    }

    const data = await response.json();
    return { 
      context: data.system_context || "", 
      metrics: data.metrics || {} 
    };
  } catch (error) {
    console.warn("Error fetching retention context:", error);
    return { context: "", metrics: {} };
  }
}

// Build comprehensive context including LangGraph causal analysis
function buildSystemContext(
  basicContext: string,
  causalAnalysis: CausalAnalysisResult | null
): string {
  let context = `You are a Retention Intelligence Agent powered by a LangGraph causal reasoning pipeline.

You have access to:
1. Customer retention data and metrics
2. Causal analysis from a 5-node LangGraph pipeline (Hypothesis Generation → Causal Testing → Confounder Analysis → Lever Estimation → Explanation)
3. Validated causal relationships and recommended interventions

`;

  // Add basic metrics context
  if (basicContext) {
    context += basicContext + "\n\n";
  }

  // Add LangGraph causal analysis results
  if (causalAnalysis) {
    context += `## 🔬 LangGraph Causal Analysis Results
Session ID: ${causalAnalysis.session_id}
Status: ${causalAnalysis.status}

### Validated Root Causes
${causalAnalysis.validated_causes?.length > 0 
  ? causalAnalysis.validated_causes.map(c => `- ✓ ${c}`).join("\n")
  : "- No validated causes found yet"}

### Recommended Intervention Levers
${causalAnalysis.recommended_levers?.length > 0
  ? causalAnalysis.recommended_levers.map(l => `- ⚡ ${l}`).join("\n")
  : "- No levers recommended yet"}

### Causal Hypotheses Tested
${causalAnalysis.hypotheses?.map(h => {
  const status = h.validated ? "✓ VALIDATED" : "✗ Not validated";
  const confidence = h.confidence ? ` (${(h.confidence * 100).toFixed(0)}% confidence)` : "";
  const effect = h.effect_size ? `, effect size: ${h.effect_size.toFixed(3)}` : "";
  return `- [${status}] ${h.cause} → ${h.effect}${confidence}${effect}
  Mechanism: ${h.mechanism}${h.causal_structure?.actionable_lever ? `\n  Actionable Lever: ${h.causal_structure.actionable_lever}` : ""}`;
}).join("\n\n") || "No hypotheses tested yet"}

### Causal Graph
Nodes: ${causalAnalysis.causal_graph?.nodes?.join(", ") || "None"}
Edges: ${causalAnalysis.causal_graph?.edges?.map(e => `${e.from} → ${e.to} (${e.strength.toFixed(2)})`).join(", ") || "None"}

### Expert Explanation
${causalAnalysis.explanation || "Analysis in progress..."}

---
`;
  } else {
    context += `## ⚠️ Causal Analysis
No causal analysis available yet. The LangGraph pipeline will run when you ask questions about retention causes.

`;
  }

  context += `## How to Use This Information
When answering questions:
1. Reference the validated causes and their confidence levels
2. Recommend the identified intervention levers
3. Explain the causal mechanisms discovered
4. Use the causal graph to show relationships
5. Be specific about effect sizes and statistical significance
6. If asked "why", refer to the tested hypotheses

You can generate charts, tables, and interactive UI components to visualize the causal relationships.`;

  return context;
}

function getDefaultContext(): string {
  return `You are a Retention Intelligence Agent. You help analyze customer retention data and provide actionable insights.

When the user asks questions:
1. Provide clear, data-driven answers
2. Use charts and tables to visualize data when appropriate
3. Generate hypotheses about causal relationships when asked about "why"
4. Suggest actionable interventions

If you don't have access to specific data, ask the user to upload their customer data files.`;
}

export async function POST(req: NextRequest) {
  const { prompt, threadId, responseId, brandId } = (await req.json()) as {
    prompt: DBMessage;
    threadId: string;
    responseId: string;
    brandId?: string;
  };

  const client = new OpenAI({
    baseURL: "https://api.thesys.dev/v1/embed/",
    apiKey: process.env.THESYS_API_KEY,
  });

  const messageStore = getMessageStore(threadId);
  messageStore.addMessage(prompt);

  // Get basic retention context from Python backend
  const { context: basicContext } = await getRetentionContext(brandId);
  
  // Run LangGraph causal analysis (5-node pipeline with Groq LLM)
  // This calls: Hypothesis Generation → Causal Testing → Confounder Analysis → Lever Estimation → Explanation
  const causalAnalysis = await getCausalAnalysis(threadId, brandId);
  
  // Build comprehensive system context including LangGraph results
  const systemContext = buildSystemContext(basicContext, causalAnalysis);

  // Build messages with system context
  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: systemContext },
    ...messageStore.getOpenAICompatibleMessageList(),
  ];

  const llmStream = await client.chat.completions.create({
    model: "c1/openai/gpt-5/v-20250915",
    messages,
    stream: true,
  });

  const responseStream = transformStream(
    llmStream,
    (chunk) => {
      return chunk.choices?.[0]?.delta?.content ?? "";
    },
    {
      onEnd: ({ accumulated }) => {
        const message = accumulated.filter((message) => message).join("");
        messageStore.addMessage({
          role: "assistant",
          content: message,
          id: responseId,
        });
      },
    }
  ) as ReadableStream<string>;

  return new NextResponse(responseStream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
