import { useEffect, useRef, useState } from "react";
import { ApiError, clearChatHistory, getChatHistory, sendChatMessage } from "../api/client";
import type { ChatMessage, Finding } from "../types/domain";
import { CONDITION_LABELS } from "../types/domain";
import { FormattedMessage } from "./FormattedMessage";

interface Props {
  caseId: string;
  readOnly?: boolean;
  findings?: Finding[];
  onHighlightFinding?: (findingId: string) => void;
}

/** Finds the finding whose condition label is mentioned in the reply text,
 * so asking "show me the cavity" can highlight it on the X-ray viewer. */
function findMentionedFinding(text: string, findings: Finding[]): Finding | undefined {
  const lower = text.toLowerCase();
  let best: Finding | undefined;
  for (const f of findings) {
    const label = CONDITION_LABELS[f.condition]?.toLowerCase();
    if (label && lower.includes(label)) {
      if (!best || f.confidence > best.confidence) best = f;
    }
  }
  return best;
}

const DEFAULT_SUMMARY_PROMPT =
  "Summarize the detected findings and give me relevant ADA guideline insights and suggestions.";

function formatTime(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function ChatPanel({ caseId, readOnly, findings = [], onHighlightFinding }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const autoStarted = useRef<string | null>(null);

  useEffect(() => {
    setMessages([]);
    setLoadingHistory(true);
    getChatHistory(caseId)
      .then((history) => {
        setMessages(history);
        if (history.length === 0 && !readOnly && findings.length > 0 && autoStarted.current !== caseId) {
          autoStarted.current = caseId;
          void handleSend(DEFAULT_SUMMARY_PROMPT);
        }
      })
      .catch(() => setMessages([]))
      .finally(() => setLoadingHistory(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  async function handleSend(overrideText?: string) {
    const text = (overrideText ?? input).trim();
    if (!text || sending) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    if (!overrideText) setInput("");
    setSending(true);
    setError(null);
    try {
      const result = await sendChatMessage(caseId, text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.reply,
          citations: result.citations,
          annotated_image: result.annotated_image,
        },
      ]);
      const mentioned = findMentionedFinding(text + " " + result.reply, findings);
      if (mentioned) onHighlightFinding?.(mentioned.finding_id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Chat request failed. Please try again.");
    } finally {
      setSending(false);
    }
  }

  async function handleReset() {
    if (clearing) return;
    setClearing(true);
    setError(null);
    try {
      await clearChatHistory(caseId);
      setMessages([]);
      if (!readOnly && findings.length > 0) {
        await handleSend(DEFAULT_SUMMARY_PROMPT);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to reset chat. Please try again.");
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-panel__header">
        <h2>Ask about this image</h2>
        {!readOnly && messages.length > 0 && (
          <button
            type="button"
            className="chat-panel__clear-btn"
            disabled={clearing || sending}
            onClick={handleReset}
          >
            {clearing ? "Resetting…" : "Reset to default"}
          </button>
        )}
      </div>
      <div className="chat-panel__messages">
        {loadingHistory && (
          <p className="chat-panel__empty">
            <span className="app__spinner" /> Loading history…
          </p>
        )}
        {!loadingHistory && messages.length === 0 && (
          <p className="chat-panel__empty">Ask a question about this X-ray or its findings.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-panel__row chat-panel__row--${m.role}`}>
            <span className={`chat-panel__avatar chat-panel__avatar--${m.role}`}>
              {m.role === "user" ? "You" : "AI"}
            </span>
            <div className={`chat-panel__message chat-panel__message--${m.role}`}>
              <FormattedMessage text={m.content} />
              {m.annotated_image && (
                <img
                  src={m.annotated_image}
                  alt="Annotated X-ray showing the discussed finding"
                  className="chat-panel__annotated-image"
                />
              )}
              {m.created_at && (
                <span className="chat-panel__timestamp">{formatTime(m.created_at)}</span>
              )}
              {m.citations && m.citations.length > 0 && (
                <span className="chat-panel__citations">
                  Sources:{" "}
                  {m.citations.map((c, ci) => (
                    <a
                      key={c.chunk_id}
                      href={c.url || undefined}
                      target="_blank"
                      rel="noreferrer"
                      className="chat-panel__citation-link"
                    >
                      [{ci + 1}] {c.source}
                    </a>
                  ))}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
      {error && (
        <p className="chat-panel__error" role="alert">
          {error}
        </p>
      )}
      {!readOnly && (
        <div className="chat-panel__input-row">
          <input
            type="text"
            className="chat-panel__input"
            placeholder="Ask a question…"
            value={input}
            disabled={sending}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend();
            }}
          />
          <button type="button" disabled={sending || !input.trim()} onClick={() => handleSend()}>
            {sending ? (
              <>
                <span className="app__spinner" /> Sending…
              </>
            ) : (
              "Send"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
