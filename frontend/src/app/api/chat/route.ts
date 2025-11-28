import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import { transformStream } from "@crayonai/stream";
import { DBMessage, getMessageStore } from "./messageStore";

// Python backend URL - configurable via environment variable
const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

// Fetch retention context from Python backend
async function getRetentionContext(brandId?: string): Promise<string> {
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
      return getDefaultContext();
    }

    const data = await response.json();
    return data.system_context || getDefaultContext();
  } catch (error) {
    console.warn("Error fetching retention context:", error);
    return getDefaultContext();
  }
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

  // Get retention context from Python backend
  const systemContext = await getRetentionContext(brandId);

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
