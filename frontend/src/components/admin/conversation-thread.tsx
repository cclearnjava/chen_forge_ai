import type { CockpitMessage } from "@/lib/admin-api";

const EXTERNAL_SOURCE_LABELS: Record<string, string> = {
  external_mock: "Mock",
  external_email: "Email",
  external_feishu: "Feishu",
  external_wechat_work: "WeCom",
};

export default function ConversationThread({ messages }: { messages: CockpitMessage[] }) {
  return (
    <section className="conversation-panel" aria-label="Conversation thread">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Conversation</p>
          <h2>客户上下文线程</h2>
        </div>
        <span>{messages.length} messages</span>
      </div>
      <div className="message-stack">
        {messages.map((message) => {
          const externalLabel = message.source?.startsWith("external_")
            ? EXTERNAL_SOURCE_LABELS[message.source] || "External"
            : null;
          return (
            <article className={`message-bubble ${message.sender_type}`} key={message.id}>
              <header>
                <strong>{message.sender_label || ""}</strong>
                <span>
                  {externalLabel && <span className="source-badge">{externalLabel}</span>}
                  {message.sender_type} · {message.source} · {new Date(message.created_at).toLocaleString()}
                </span>
              </header>
              <p>{message.body_markdown}</p>
            </article>
          );
        })}
      </div>
      <form className="message-composer" onSubmit={(e) => e.preventDefault()}>
        <label>
          人工跟进记录
          <textarea
            rows={4}
            placeholder="写一条 owner message。此 UI 为占位，接 Conversation API 后启用。"
            defaultValue=""
          />
        </label>
        <div>
          <span>source: manual · sender: owner</span>
          <button className="button primary" type="button" disabled>Add Message (API pending)</button>
        </div>
      </form>
    </section>
  );
}
