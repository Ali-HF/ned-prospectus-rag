import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  Send,
  Sliders,
  ChevronUp
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
  const [heroExpanded, setHeroExpanded] = useState<boolean>(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const statusOptions = ["Retrieving...", "Sleuthing...", "Honing...", "Triangulating..."];

  const hasConversations = messages.length > 1;

  // Auto-collapse hero when conversation starts, while allowing user to toggle
  useEffect(() => {
    if (hasConversations) {
      setHeroExpanded(false);
    }
  }, [hasConversations]);

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
    } catch {
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
    setHeroExpanded(true);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        maxHeight: "100vh",
        width: "100%",
        overflow: "hidden",
      }}
    >
      {/* Sleek Minimalist Navigation Bar */}
      <header
        style={{
          height: "56px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0 1.5rem",
          background: "rgba(10, 13, 18, 0.75)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.07)",
          flexShrink: 0,
          zIndex: 40,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: "linear-gradient(135deg, #ff551f, #e04410)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 800,
              fontSize: "0.78rem",
              color: "#fff",
              boxShadow: "0 0 14px rgba(255, 85, 31, 0.35)",
              letterSpacing: "0.02em",
            }}
          >
            NED
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span
              style={{
                fontFamily: "Space Grotesk, sans-serif",
                fontWeight: 700,
                fontSize: "0.95rem",
                letterSpacing: "-0.01em",
                color: "#f8fafc",
              }}
            >
              Prospectus Intel
            </span>
            <span
              style={{
                fontSize: "0.68rem",
                color: "#64748b",
                fontFamily: "Space Grotesk, monospace",
                fontWeight: 500,
              }}
            >
              v2025 // RAG
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Subtle Live Badge */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "3px 9px",
              background: "rgba(34, 197, 94, 0.08)",
              border: "1px solid rgba(34, 197, 94, 0.2)",
              borderRadius: 20,
              color: "#4ade80",
              fontSize: "0.7rem",
              fontFamily: "Space Grotesk, monospace",
              fontWeight: 500,
            }}
          >
            <span
              style={{
                width: 5,
                height: 5,
                backgroundColor: "#22c55e",
                borderRadius: "50%",
                boxShadow: "0 0 6px #22c55e",
              }}
            />
            122 Pgs Active
          </div>

          {/* Citations Toggle Button */}
          <button
            onClick={() => setShowSources(!showSources)}
            title="Toggle citation references"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              background: showSources ? "rgba(255, 85, 31, 0.12)" : "rgba(255, 255, 255, 0.03)",
              border: `1px solid ${showSources ? "rgba(255, 85, 31, 0.35)" : "rgba(255, 255, 255, 0.07)"}`,
              color: showSources ? "#ff723f" : "#94a3b8",
              padding: "4px 10px",
              borderRadius: 6,
              fontSize: "0.72rem",
              fontFamily: "Space Grotesk, sans-serif",
              fontWeight: 500,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <Sliders size={12} />
            <span>{showSources ? "Citations" : "Muted"}</span>
          </button>

          {/* Reset Conversation Button */}
          <button
            onClick={handleReset}
            title="Reset conversation"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.07)",
              color: "#94a3b8",
              padding: "4px 10px",
              borderRadius: 6,
              fontSize: "0.72rem",
              fontFamily: "Space Grotesk, sans-serif",
              fontWeight: 500,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <RotateCcw size={12} />
            <span>Reset</span>
          </button>
        </div>
      </header>

      {/* Main Content Area: Scrollable Chat Container */}
      <main
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "1rem 1.25rem 0.5rem",
          scrollBehavior: "smooth",
        }}
      >
        <div style={{ width: "100%", maxWidth: 860, margin: "0 auto", display: "flex", flexDirection: "column" }}>
          
          {/* Collapsible / Dismissible Hero Section */}
          <AnimatePresence>
            {heroExpanded ? (
              <motion.section
                key="hero-expanded"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0, overflow: "hidden" }}
                transition={{ duration: 0.45, ease: "easeInOut" }}
                style={{
                  marginBottom: "1.5rem",
                  padding: "1.5rem",
                  background: "rgba(14, 18, 25, 0.5)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                  borderRadius: 14,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {/* Minimize button if there's ongoing chat */}
                {hasConversations && (
                  <button
                    onClick={() => setHeroExpanded(false)}
                    style={{
                      position: "absolute",
                      top: 12,
                      right: 12,
                      background: "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      color: "#94a3b8",
                      borderRadius: 6,
                      padding: "4px 8px",
                      fontSize: "0.7rem",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    <span>Collapse</span>
                    <ChevronUp size={12} />
                  </button>
                )}

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1.3fr 0.7fr",
                    gap: "2rem",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        color: "#ff551f",
                        fontFamily: "Space Grotesk, monospace",
                        fontWeight: 600,
                        fontSize: "0.72rem",
                        letterSpacing: "0.12em",
                        marginBottom: "0.75rem",
                        textTransform: "uppercase",
                      }}
                    >
                      <span
                        style={{
                          width: 5,
                          height: 5,
                          borderRadius: "50%",
                          background: "#ff551f",
                          boxShadow: "0 0 8px #ff551f",
                        }}
                      />
                      NED UNIVERSITY ADMISSIONS COPILOT
                    </div>

                    <h1
                      style={{
                        fontFamily: "Space Grotesk, sans-serif",
                        fontSize: "2.4rem",
                        fontWeight: 700,
                        lineHeight: 1.12,
                        letterSpacing: "-0.03em",
                        color: "#ffffff",
                        marginBottom: "0.75rem",
                      }}
                    >
                      Admissions intelligence,{" "}
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

                    <p
                      style={{
                        fontSize: "0.92rem",
                        lineHeight: 1.55,
                        color: "#94a3b8",
                        marginBottom: "1.25rem",
                      }}
                    >
                      Strictly grounded in the official <strong>NED Undergraduate Prospectus 2025</strong>. Verifiable citations, exact merit rules, eligibility benchmarks, and fee schedules.
                    </p>

                    {/* Stats strip */}
                    <div style={{ display: "flex", gap: "1.75rem" }}>
                      <div>
                        <div style={{ fontFamily: "Space Grotesk", fontSize: "1.25rem", fontWeight: 700, color: "#fff" }}>122</div>
                        <div style={{ fontSize: "0.68rem", color: "#64748b", fontFamily: "Space Grotesk", textTransform: "uppercase" }}>Pages Indexed</div>
                      </div>
                      <div>
                        <div style={{ fontFamily: "Space Grotesk", fontSize: "1.25rem", fontWeight: 700, color: "#fff" }}>562</div>
                        <div style={{ fontSize: "0.68rem", color: "#64748b", fontFamily: "Space Grotesk", textTransform: "uppercase" }}>Neural Chunks</div>
                      </div>
                      <div>
                        <div style={{ fontFamily: "Space Grotesk", fontSize: "1.25rem", fontWeight: 700, color: "#fff" }}>0.62</div>
                        <div style={{ fontSize: "0.68rem", color: "#64748b", fontFamily: "Space Grotesk", textTransform: "uppercase" }}>Cutoff Filter</div>
                      </div>
                      <div>
                        <div style={{ fontFamily: "Space Grotesk", fontSize: "1.25rem", fontWeight: 700, color: "#fff" }}>0.0s</div>
                        <div style={{ fontSize: "0.68rem", color: "#64748b", fontFamily: "Space Grotesk", textTransform: "uppercase" }}>Safety Shield</div>
                      </div>
                    </div>
                  </div>

                  {/* Slower, subtle Medallion Graphic (160s rotation) */}
                  <div style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
                    <motion.svg
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 160, ease: "linear" }}
                      style={{ width: "100%", maxWidth: 220, filter: "drop-shadow(0 0 25px rgba(255, 85, 31, 0.15))" }}
                      viewBox="0 0 400 400"
                      fill="none"
                    >
                      <circle cx="200" cy="200" r="190" stroke="#ff551f" strokeWidth="1.2" strokeDasharray="4 6" opacity="0.4" />
                      <circle cx="200" cy="200" r="176" stroke="#ffffff" strokeWidth="1" opacity="0.2" />
                      <circle cx="200" cy="200" r="148" stroke="#ffffff" strokeWidth="0.75" strokeDasharray="2 4" opacity="0.25" />
                      <circle cx="200" cy="200" r="100" stroke="#ff551f" strokeWidth="1.5" opacity="0.5" />
                      
                      <polygon points="200,10 206,180 200,200 194,180" fill="#ff551f" />
                      <polygon points="200,390 206,220 200,200 194,220" fill="#ffffff" opacity="0.4" />
                      <polygon points="10,200 180,206 200,200 180,194" fill="#ffffff" opacity="0.4" />
                      <polygon points="390,200 220,206 200,200 220,194" fill="#ffffff" opacity="0.4" />

                      <circle cx="200" cy="200" r="62" fill="#0d1117" stroke="#ff551f" strokeWidth="2" />
                      <circle cx="200" cy="200" r="42" stroke="#ffffff" strokeWidth="1" strokeDasharray="3 3" opacity="0.5" />
                      <polygon points="200,165 210,190 235,190 215,205 222,230 200,215 178,230 185,205 165,190 190,190" fill="#ff551f" opacity="0.85" />
                      <circle cx="200" cy="200" r="10" fill="#ffffff" />
                    </motion.svg>
                  </div>
                </div>
              </motion.section>
            ) : (
              /* Mini collapsed summary ribbon */
              <motion.div
                key="hero-collapsed"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "6px 14px",
                  background: "rgba(14, 18, 25, 0.45)",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                  borderRadius: 8,
                  marginBottom: "1rem",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.78rem", color: "#94a3b8" }}>
                  <span style={{ color: "#ff551f", fontWeight: 600, fontFamily: "Space Grotesk" }}>NED Copilot</span>
                  <span>•</span>
                  <span>122 Pages Indexed</span>
                  <span>•</span>
                  <span style={{ color: "#64748b" }}>Prospectus 2025</span>
                </div>
                <button
                  onClick={() => setHeroExpanded(true)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#ff723f",
                    fontSize: "0.72rem",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 3,
                    fontFamily: "Space Grotesk",
                  }}
                >
                  <span>Show Overview</span>
                  <ChevronDown size={13} />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Quick Starter Prompts */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: "1.25rem" }}>
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
                  border: "1px solid rgba(255, 255, 255, 0.07)",
                  color: "#cbd5e1",
                  padding: "6px 11px",
                  borderRadius: 6,
                  fontSize: "0.78rem",
                  fontFamily: "Space Grotesk, sans-serif",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 5,
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255, 85, 31, 0.4)";
                  e.currentTarget.style.color = "#ffffff";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.07)";
                  e.currentTarget.style.color = "#cbd5e1";
                }}
              >
                <Sparkles size={11} color="#ff551f" />
                <span>{prompt}</span>
              </button>
            ))}
          </div>

          {/* Messages Flow Container */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginBottom: "1rem" }}>
            <AnimatePresence>
              {messages.map((msg, index) => {
                const isUser = msg.role === "user";
                return (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25 }}
                    style={{
                      background: isUser ? "rgba(20, 24, 32, 0.65)" : "rgba(14, 18, 25, 0.82)",
                      border: `1px solid ${isUser ? "rgba(255, 255, 255, 0.06)" : "rgba(255, 255, 255, 0.08)"}`,
                      borderLeft: isUser ? "3px solid rgba(255, 255, 255, 0.25)" : "3px solid #ff551f",
                      borderRadius: 10,
                      padding: "1.1rem 1.4rem",
                      boxShadow: "0 4px 20px rgba(0, 0, 0, 0.22)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "0.5rem" }}>
                      <div
                        style={{
                          fontFamily: "Space Grotesk, sans-serif",
                          fontSize: "0.72rem",
                          fontWeight: 700,
                          color: isUser ? "#cbd5e1" : "#ff723f",
                          letterSpacing: "0.06em",
                          textTransform: "uppercase",
                        }}
                      >
                        {isUser ? "PROSPECTIVE APPLICANT" : "NED GUIDE // OFFICIAL ASSISTANT"}
                      </div>
                    </div>

                    <div style={{ fontSize: "0.95rem", lineHeight: 1.65, color: "#f1f5f9", whiteSpace: "pre-wrap" }}>
                      {msg.content}
                    </div>

                    {/* Collapsible Verified Citations Dropdown */}
                    {showSources && msg.sources && msg.sources.length > 0 && (
                      <div style={{ marginTop: "0.85rem" }}>
                        <button
                          onClick={() => toggleCitation(index)}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            background: "rgba(255, 85, 31, 0.08)",
                            border: "1px solid rgba(255, 85, 31, 0.22)",
                            color: "#fdba74",
                            padding: "4px 10px",
                            borderRadius: 6,
                            fontSize: "0.74rem",
                            fontFamily: "Space Grotesk, monospace",
                            cursor: "pointer",
                          }}
                        >
                          {openCitations[index] ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                          <span>VERIFIED SOURCES ({msg.sources.length} CITATIONS)</span>
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
                                gap: 6,
                                paddingTop: "0.6rem",
                              }}
                            >
                              {msg.sources.map((s, si) => (
                                <span
                                  key={si}
                                  style={{
                                    background: "rgba(0, 0, 0, 0.4)",
                                    border: "1px solid rgba(255, 85, 31, 0.25)",
                                    padding: "3px 8px",
                                    borderRadius: 4,
                                    fontSize: "0.7rem",
                                    fontFamily: "Space Grotesk, monospace",
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
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  background: "rgba(16, 20, 28, 0.85)",
                  border: "1px solid rgba(255, 85, 31, 0.3)",
                  borderLeft: "3px solid #ff551f",
                  borderRadius: 10,
                  padding: "0.85rem 1.25rem",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
                  style={{
                    width: 15,
                    height: 15,
                    border: "2px solid #ff551f",
                    borderTopColor: "transparent",
                    borderRadius: "50%",
                  }}
                />
                <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: "0.85rem", color: "#ff8555", fontWeight: 600 }}>
                  {statusText}
                </div>
                <div style={{ fontSize: "0.72rem", color: "#64748b", fontFamily: "Space Grotesk, sans-serif" }}>
                  Scanning prospectus index & verifying factual citations...
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      {/* Sleek Fixed Input Dock at the bottom */}
      <footer
        style={{
          width: "100%",
          padding: "0.75rem 1.25rem 1rem",
          background: "linear-gradient(to top, rgba(8, 9, 11, 0.98) 70%, rgba(8, 9, 11, 0))",
          flexShrink: 0,
          zIndex: 30,
        }}
      >
        <div
          style={{
            maxWidth: 860,
            margin: "0 auto",
            background: "rgba(14, 18, 25, 0.88)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: 12,
            padding: "6px 10px 6px 14px",
            display: "flex",
            alignItems: "center",
            gap: 10,
            boxShadow: "0 8px 30px rgba(0, 0, 0, 0.5)",
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about merit criteria, quota seats, eligibility, or fee schedules..."
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "#ffffff",
              fontSize: "0.92rem",
              fontFamily: "Inter, sans-serif",
              padding: "6px 4px",
            }}
          />

          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            style={{
              background: input.trim() ? "#ff551f" : "rgba(255, 255, 255, 0.05)",
              border: "none",
              color: "#fff",
              padding: "8px 16px",
              borderRadius: 8,
              cursor: input.trim() ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontFamily: "Space Grotesk, sans-serif",
              fontWeight: 700,
              fontSize: "0.8rem",
              boxShadow: input.trim() ? "0 0 14px rgba(255, 85, 31, 0.4)" : "none",
              transition: "all 0.15s ease",
            }}
          >
            <span>TRANSMIT</span>
            <Send size={13} />
          </button>
        </div>
      </footer>
    </div>
  );
}
