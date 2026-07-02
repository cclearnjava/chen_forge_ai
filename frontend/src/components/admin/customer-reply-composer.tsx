"use client";

import { useState } from "react";
import { recordCustomerReply } from "@/lib/admin-api";

function errorMessage(err: unknown): string {
  if (!(err instanceof Error)) return "Unknown error";
  const msg = err.message;
  if (msg.includes("404")) return "机会不存在";
  if (msg.includes("422")) return "对话上下文不完整";
  return msg;
}

export default function CustomerReplyComposer({
  opportunityId,
  onRecorded,
}: {
  opportunityId: string;
  onRecorded?: () => void;
}) {
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!body.trim()) return;
    setSending(true);
    setError(null);
    try {
      await recordCustomerReply(opportunityId, { body_markdown: body.trim() });
      setBody("");
      onRecorded?.();
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setSending(false);
    }
  };

  return (
    <form
      className="message-composer customer-reply"
      onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
      aria-label="Record customer reply"
    >
      <label>
        录入客户回复
        <textarea
          rows={3}
          placeholder="客户通过微信/邮件/电话回复的内容..."
          value={body}
          onChange={(e) => setBody(e.target.value)}
          disabled={sending}
        />
      </label>
      {error && <p className="error-msg">{error}</p>}
      <div>
        <span>source: manual · sender_type: customer</span>
        <button className="button primary" type="submit" disabled={sending || !body.trim()}>
          {sending ? "Recording..." : "Record customer reply"}
        </button>
      </div>
    </form>
  );
}
