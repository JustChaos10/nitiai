"use client";

import Link from "next/link";
import { C1Chat } from "@thesysai/genui-sdk";
import "@crayonai/react-ui/styles/index.css";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#ededed] flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex-shrink-0">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-semibold">Retention Reasoning Agent</h1>
          <nav className="flex gap-4">
            <Link href="/" className="text-white font-medium">
              Chat
            </Link>
            <Link href="/analysis" className="text-gray-400 hover:text-white transition">
              Analysis
            </Link>
          </nav>
        </div>
      </header>
      
      {/* Chat Container */}
      <div className="flex-1 overflow-hidden">
        <C1Chat apiUrl="/api/chat" theme={{ mode: "dark" }} />
      </div>
    </div>
  );
}
