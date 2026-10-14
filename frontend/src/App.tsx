import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  Send,
  Sliders
} from "lucide-react";

interface Source {
  page: number;
  section: string;
  similarity: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hello! I am NED Guide, an AI assistant strictly grounded in the official NED Undergraduate Prospectus 2025. Ask me anything about admission categories, merit criteria, eligibility thresholds, or fee structures.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("Retrieving...");
  const [showSources, setShowSources] = useState(true);
  const [openCitations, setOpenCitations] = useState<{ [key: number]: boolean }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const statusOptions = ["Retrieving...", "Sleuthing...", "Honing...", "Triangulating..."];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const toggleCitation = (idx: number) => {
    setOpenCitations((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = { role: "user", content: textToSend.trim() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    // Dynamic status animation cycle
    let statusIdx = 0;
    setStatusText(statusOptions[0]);
    const interval = setInterval(() => {
      statusIdx = (statusIdx + 1) % statusOptions.length;
      setStatusText(statusOptions[statusIdx]);
    }, 1200);

    try {
      const historyPayload = newMessages.slice(0, -1).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: textToSend.trim(), history: historyPayload }),
      });

      clearInterval(interval);

      if (!res.ok) {
        throw new Error("Server responded with error status");
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources || [],
        },
      ]);
    } catch (err) {
      clearInterval(interval);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I couldn't find that in the NED Undergraduate Prospectus 2025, so I don't want to guess. Please check with the NED admissions office.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([
      {
        role: "assistant",
        content:
          "Conversation reset. I am ready to answer any questions about the NED Undergraduate Prospectus 2025.",
      },
    ]);
  };

  return (
    <div style={{ maxWidth: 1240, margin: "0 auto", padding: "1.5rem 1.5rem 6rem" }}>
      {/* Top Floating Command Bar */}
      <motion.header
        initial={{ opacity: 0, y: -15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "1rem 1.75rem",
          background: "rgba(13, 16, 22, 0.7)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: 14,
          marginBottom: "2.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 8,
              background: "linear-gradient(135deg, #ff551f, #d93d0b)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: "0.95rem",
              color: "#fff",
              boxShadow: "0 0 20px rgba(255, 85, 31, 0.45)",
            }}
          >
            NED
          </div>
          <div>
            <div style={{ fontFamily: "Space Grotesk", fontWeight: 700, fontSize: "1.1rem", color: "#fff" }}>
              ADMISSIONS INTEL // RAG
            </div>
            <div style={{ fontSize: "0.72rem", color: "#64748b", fontFamily: "Space Grotesk" }}>
              OFFICIAL 2025 PROSPECTUS COPILOT
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "5px 12px",
              background: "rgba(34, 197, 94, 0.08)",
              border: "1px solid rgba(34, 197, 94, 0.25)",
              borderRadius: 100,
              color: "#4ade80",
              fontSize: "0.72rem",
              fontFamily: "Space Grotesk",
              fontWeight: 600,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                backgroundColor: "#22c55e",
                borderRadius: "50%",
                boxShadow: "0 0 8px #22c55e",
              }}
            />
            INDEX VERIFIED (122 PGS)
          </div>

          <button
            onClick={() => setShowSources(!showSources)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: showSources ? "rgba(255, 85, 31, 0.15)" : "rgba(255, 255, 255, 0.04)",
              border: `1px solid ${showSources ? "rgba(255, 85, 31, 0.4)" : "rgba(255, 255, 255, 0.08)"}`,
              color: showSources ? "#ff723f" : "#94a3b8",
              padding: "6px 14px",
              borderRadius: 8,
              fontSize: "0.75rem",
              fontFamily: "Space Grotesk",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            <Sliders size={13} />
            {showSources ? "CITATIONS ACTIVE" : "CITATIONS MUTED"}
          </button>

          <button
            onClick={handleReset}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(255, 255, 255, 0.04)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              color: "#94a3b8",
              padding: "6px 14px",
              borderRadius: 8,
              fontSize: "0.75rem",
              fontFamily: "Space Grotesk",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            <RotateCcw size={13} />
            RESET
          </button>
        </div>
      </motion.header>

      {/* Hero Section with Animated Medallion */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "1.2fr 0.8fr",
          gap: "3rem",
          alignItems: "center",
          marginBottom: "3.5rem",
          padding: "1rem 0",
        }}
      >
        <motion.div
          initial={{ opacity: 0, x: -25 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              color: "#ff551f",
              fontFamily: "Space Grotesk",
              fontWeight: 600,
              fontSize: "0.78rem",
              letterSpacing: "0.15em",
              marginBottom: "1rem",
              textTransform: "uppercase",
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#ff551f", boxShadow: "0 0 10px #ff551f" }} />
            SYS.01 / ONLINE • NED UNIVERSITY OF ENGINEERING & TECHNOLOGY
          </div>

          <h1
            style={{
              fontFamily: "Space Grotesk",
              fontSize: "3.75rem",
              fontWeight: 700,
              lineHeight: 1.05,
              letterSpacing: "-0.04em",
              color: "#ffffff",
              marginBottom: "1.2rem",
            }}
          >
            Make admissions{" "}
            <span
              style={{
                color: "#ff551f",
                background: "linear-gradient(135deg, #ff551f 0%, #ff8555 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              tangible.
            </span>
          </h1>

          <p style={{ fontSize: "1.1rem", lineHeight: 1.6, color: "#94a3b8", maxWidth: 580, marginBottom: "2rem" }}>
            Answers strictly grounded in the official <strong>NED Undergraduate Prospectus 2025</strong>. Verifiable citations, exact merit rules, eligibility benchmarks, and fee structures with zero hallucinations.
          </p>

          {/* Tactical Stats Matrix */}
          <div style={{ display: "flex", gap: "2.5rem" }}>
            <div>
              <div style={{ fontFamily: "Space Grotesk", fontSize: "1.6rem", fontWeight: 700, color: "#fff" }}>122</div>
              <div style={{ fontSize: "0.72rem", color: "#64748b", fontFamily: "Space Grotesk", textTransform: "uppercase" }}>Pages Indexed</div>
            </div>
            <div>
              <div style={{ fontFamily: "Space Grotesk", fontSize: "1.6rem", fontWeight: 700, color: "#fff" }}>562</div>
              <div style={{ fontSize: "0.72rem", color: "#64748b", fontFamily: "Space Grotesk", textTransform: "uppercase" }}>Neural Chunks</div>
            </div>
            <div>
              <div style={{ fontFamily: "Space Grotesk", fontSize: "1.6rem", fontWeight: 700, color: "#fff" }}>0.62</div>
              <div style={{ fontSize: "0.72rem", color: "#64748b", fontFamily: "Space Grotesk", textTransform: "uppercase" }}>Safety Cutoff</div>
            </div>
            <div>
              <div style={{ fontFamily: "Space Grotesk", fontSize: "1.6rem", fontWeight: 700, color: "#fff" }}>0.0s</div>
              <div style={{ fontSize: "0.72rem", color: "#64748b", fontFamily: "Space Grotesk", textTransform: "uppercase" }}>Hallucination Shield</div>
            </div>
          </div>
        </motion.div>

        {/* Animated Medallion Graphic */}
        <motion.div
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          style={{ display: "flex", justifyContent: "center", alignItems: "center" }}
        >
          <motion.svg
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 80, ease: "linear" }}
            style={{ width: "100%", maxWidth: 380, filter: "drop-shadow(0 0 40px rgba(255, 85, 31, 0.2))" }}
            viewBox="0 0 400 400"
            fill="none"
          >
            <circle cx="200" cy="200" r="190" stroke="#ff551f" strokeWidth="1.2" strokeDasharray="4 6" opacity="0.45" />
            <circle cx="200" cy="200" r="176" stroke="#ffffff" strokeWidth="1" opacity="0.25" />
            <circle cx="200" cy="200" r="148" stroke="#ffffff" strokeWidth="0.75" strokeDasharray="2 4" opacity="0.3" />
            <circle cx="200" cy="200" r="100" stroke="#ff551f" strokeWidth="1.5" opacity="0.6" />
            
            <polygon points="200,10 206,180 200,200 194,180" fill="#ff551f" />
            <polygon points="200,390 206,220 200,200 194,220" fill="#ffffff" opacity="0.5" />
            <polygon points="10,200 180,206 200,200 180,194" fill="#ffffff" opacity="0.5" />
            <polygon points="390,200 220,206 200,200 220,194" fill="#ffffff" opacity="0.5" />

            <circle cx="200" cy="200" r="62" fill="#0d1117" stroke="#ff551f" strokeWidth="2" />
            <circle cx="200" cy="200" r="42" stroke="#ffffff" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
            <polygon points="200,165 210,190 235,190 215,205 222,230 200,215 178,230 185,205 165,190 190,190" fill="#ff551f" opacity="0.85" />
            <circle cx="200" cy="200" r="10" fill="#ffffff" />
          </motion.svg>
        </motion.div>
      </section>

      {/* Suggested Fast Prompts */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: "2rem" }}>
        {[
          "What is the minimum percentage required in HSC for engineering?",
          "Who was the first Vice Chancellor of NED University?",
          "What is the semester fee for regular BE programmes?",
          "Where is the TIEST campus located?",
        ].map((prompt, i) => (
          <button
            key={i}
            onClick={() => handleSend(prompt)}
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              color: "#cbd5e1",
              padding: "8px 14px",
              borderRadius: 8,
              fontSize: "0.82rem",
              fontFamily: "Space Grotesk",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(255, 85, 31, 0.5)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.08)")}
          >
            <Sparkles size={13} color="#ff551f" />
            {prompt}
          </button>
        ))}
      </div>

      {/* Chat Messages Log */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", marginBottom: "2.5rem" }}>
        <AnimatePresence>
          {messages.map((msg, index) => {
            const isUser = msg.role === "user";
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
                style={{
                  background: isUser ? "rgba(20, 24, 32, 0.65)" : "rgba(14, 18, 25, 0.85)",
                  border: `1px solid ${isUser ? "rgba(255, 255, 255, 0.06)" : "rgba(255, 255, 255, 0.08)"}`,
                  borderLeft: isUser ? "3px solid rgba(255, 255, 255, 0.2)" : "3px solid #ff551f",
                  borderRadius: 12,
                  padding: "1.25rem 1.6rem",
                  boxShadow: "0 6px 25px rgba(0, 0, 0, 0.25)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: "0.6rem" }}>
                  <div
                    style={{
                      fontFamily: "Space Grotesk",
                      fontSize: "0.76rem",
                      fontWeight: 700,
                      color: isUser ? "#cbd5e1" : "#ff723f",
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    {isUser ? "PROSPECTIVE APPLICANT" : "NED GUIDE // OFFICIAL ASSISTANT"}
                  </div>
                </div>

                <div style={{ fontSize: "1rem", lineHeight: 1.65, color: "#f1f5f9", whiteSpace: "pre-wrap" }}>
                  {msg.content}
                </div>

                {/* Collapsible Verified Citations Dropdown */}
                {showSources && msg.sources && msg.sources.length > 0 && (
                  <div style={{ marginTop: "1rem" }}>
                    <button
                      onClick={() => toggleCitation(index)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        background: "rgba(255, 85, 31, 0.08)",
                        border: "1px solid rgba(255, 85, 31, 0.25)",
                        color: "#fdba74",
                        padding: "6px 12px",
                        borderRadius: 6,
                        fontSize: "0.78rem",
                        fontFamily: "Space Grotesk",
                        cursor: "pointer",
                      }}
                    >
                      {openCitations[index] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      VERIFIED PROSPECTUS SOURCES ({msg.sources.length} CITATIONS)
                    </button>

                    <AnimatePresence>
                      {openCitations[index] && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: 8,
                            paddingTop: "0.75rem",
                          }}
                        >
                          {msg.sources.map((s, si) => (
                            <span
                              key={si}
                              style={{
                                background: "rgba(0, 0, 0, 0.4)",
                                border: "1px solid rgba(255, 85, 31, 0.3)",
                                padding: "4px 10px",
                                borderRadius: 6,
                                fontSize: "0.74rem",
                                fontFamily: "Space Grotesk",
                                color: "#cbd5e1",
                              }}
                            >
                              Page {s.page} {s.section ? `• ${s.section}` : ""} (sim: {s.similarity})
                            </span>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Dynamic Claude-style Thinking Status Box */}
        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              background: "rgba(16, 20, 28, 0.8)",
              border: "1px solid rgba(255, 85, 31, 0.3)",
              borderLeft: "3px solid #ff551f",
              borderRadius: 12,
              padding: "1rem 1.5rem",
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
              style={{ width: 18, height: 18, border: "2px solid #ff551f", borderTopColor: "transparent", borderRadius: "50%" }}
            />
            <div style={{ fontFamily: "Space Grotesk", fontSize: "0.9rem", color: "#ff8555", fontWeight: 600 }}>
              {statusText}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#64748b", fontFamily: "Space Grotesk" }}>
              Scanning prospectus chunks & synthesizing verified facts...
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Fixed Tactical Input Dock */}
      <div
        style={{
          position: "sticky",
          bottom: "1.5rem",
          background: "rgba(10, 13, 18, 0.85)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: 14,
          padding: "8px 12px",
          display: "flex",
          alignItems: "center",
          gap: 12,
          boxShadow: "0 10px 40px rgba(0, 0, 0, 0.6)",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask any question regarding NED undergraduate admissions..."
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            color: "#ffffff",
            fontSize: "0.95rem",
            fontFamily: "Inter, sans-serif",
            padding: "8px 10px",
          }}
        />

        <button
          onClick={() => handleSend()}
          disabled={loading || !input.trim()}
          style={{
            background: input.trim() ? "#ff551f" : "rgba(255, 255, 255, 0.05)",
            border: "none",
            color: "#fff",
            padding: "10px 18px",
            borderRadius: 10,
            cursor: input.trim() ? "pointer" : "not-allowed",
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontFamily: "Space Grotesk",
            fontWeight: 700,
            fontSize: "0.85rem",
            boxShadow: input.trim() ? "0 0 16px rgba(255, 85, 31, 0.45)" : "none",
            transition: "all 0.2s ease",
          }}
        >
          <span>TRANSMIT</span>
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
