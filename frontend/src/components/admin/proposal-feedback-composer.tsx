"use client";

import { useState } from "react";
import { recordProposalFeedback } from "@/lib/admin-api";

function errorMessage(err: unknown): string {
  if (!(err instanceof Error)) return "Unknown error";
  const msg = err.message;
  if (msg.includes("404")) return "机会不存在";
  if (msg.includes("422") && msg.includes("sent")) return "需要先发送 Proposal 后才能录入反馈";
  if (msg.includes("422")) return "对话上下文不完整";
  return msg;
}

export default function ProposalFeedbackComposer({
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
      await recordProposalFeedback(opportunityId, { body_markdown: body.trim() });
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
      className="message-composer proposal-feedback"
      onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
      aria-label="Record proposal feedback"
    >
      <label>
        录入客户对 Proposal 的反馈
        <textarea
          rows={3}
          placeholder="客户对 Proposal 的反馈内容（预算/范围/周期/安全等）..."
          value={body}
          onChange={(e) => setBody(e.target.value)}
          disabled={sending}
        />
      </label>
      {error && <p className="error-msg">{error}</p>}
      <div>
        <span>source: proposal_feedback · sender_type: customer</span>
        <button className="button primary" type="submit" disabled={sending || !body.trim()}>
          {sending ? "Recording..." : "Record proposal feedback"}
        </button>
      </div>
    </form>
  );
}
