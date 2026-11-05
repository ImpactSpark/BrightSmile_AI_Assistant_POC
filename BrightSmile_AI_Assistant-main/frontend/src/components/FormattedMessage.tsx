import { Fragment } from "react";

/** Renders the small markdown subset the chat LLM actually produces
 * (bold via **text**, "- " bullet lines) without pulling in a full
 * markdown library for one feature. */
function renderInline(text: string, keyPrefix: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return <Fragment key={`${keyPrefix}-${i}`}>{part}</Fragment>;
  });
}

export function FormattedMessage({ text }: { text: string }) {
  const lines = text.split("\n").filter((l) => l.trim() !== "");
  const blocks: { type: "list" | "para"; lines: string[] }[] = [];

  for (const line of lines) {
    const isBullet = /^[-*]\s+/.test(line.trim());
    const content = line.trim().replace(/^[-*]\s+/, "");
    const last = blocks[blocks.length - 1];
    if (isBullet) {
      if (last?.type === "list") last.lines.push(content);
      else blocks.push({ type: "list", lines: [content] });
    } else {
      if (last?.type === "para") last.lines.push(content);
      else blocks.push({ type: "para", lines: [content] });
    }
  }

  return (
    <>
      {blocks.map((block, bi) =>
        block.type === "list" ? (
          <ul key={bi} className="chat-panel__message-list">
            {block.lines.map((line, li) => (
              <li key={li}>{renderInline(line, `${bi}-${li}`)}</li>
            ))}
          </ul>
        ) : (
          <p key={bi} className="chat-panel__message-para">
            {block.lines.map((line, li) => (
              <Fragment key={li}>
                {li > 0 && <br />}
                {renderInline(line, `${bi}-${li}`)}
              </Fragment>
            ))}
          </p>
        )
      )}
    </>
  );
}
