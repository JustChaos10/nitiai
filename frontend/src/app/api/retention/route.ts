import { NextRequest, NextResponse } from "next/server";

// Python backend URL
const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const brandId = searchParams.get("brand_id");
  const days = searchParams.get("days") || "30";

  try {
    const response = await fetch(
      `${PYTHON_API_URL}/context?brand_id=${brandId || ""}&days=${days}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`Python API returned ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching retention context:", error);
    return NextResponse.json(
      { error: "Failed to fetch retention data" },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action, ...params } = body;

    let endpoint = "/context";
    let method = "GET";

    switch (action) {
      case "analyze":
        endpoint = "/analyze/from-data";
        method = "POST";
        break;
      case "summary":
        endpoint = "/data/summary";
        method = "GET";
        break;
      case "context":
      default:
        endpoint = "/context";
        method = "GET";
    }

    const url = `${PYTHON_API_URL}${endpoint}`;
    const response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: method === "POST" ? JSON.stringify(params) : undefined,
    });

    if (!response.ok) {
      throw new Error(`Python API returned ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error calling Python API:", error);
    return NextResponse.json(
      { error: "Failed to call retention API" },
      { status: 500 }
    );
  }
}

