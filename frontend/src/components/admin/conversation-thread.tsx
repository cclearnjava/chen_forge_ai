import type { ConversationMessage } from "@/lib/admin-mock";

export default function ConversationThread({ messages }: { messages: ConversationMessage[] }) {
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
        {messages.map((message) => (
          <article className={`message-bubble ${message.senderType}`} key={message.id}>
            <header>
              <strong>{message.senderLabel}</strong>
              <span>{message.senderType} · {message.source} · {message.createdAt}</span>
            </header>
            <p>{message.body}</p>
          </article>
        ))}
      </div>
      <form className="message-composer">
        <label>
          人工跟进记录
          <textarea
            rows={4}
            placeholder="写一条 owner message。静态 mock 中不会真实发送，后续会接 Conversation API。"
            defaultValue="张总好，我先确认三件事：资料范围、审批人、PoC 成功指标。"
          />
        </label>
        <div>
          <span>source: manual · sender: owner</span>
          <button className="button primary" type="button">Add Message</button>
        </div>
      </form>
    </section>
  );
}
