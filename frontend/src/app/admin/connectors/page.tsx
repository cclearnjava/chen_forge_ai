"use client";

import { useCallback, useEffect, useState } from "react";
import AdminShell from "@/components/admin/admin-shell";
import {
  createConnector, getConnectors, getNotificationSummary, sendMockInboundMessage, updateConnector,
  type ExternalConnectorOut, type InboundMessageResult,
} from "@/lib/admin-api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

const PROVIDER_LABELS: Record<string, string> = {
  mock: "Mock", email: "Email", feishu: "Feishu", wechat_work: "WeCom",
};
const STATUS_LABELS: Record<string, string> = {
  active: "已启用", paused: "已暂停", disabled: "已停用",
};

function webhookUrl(c: ExternalConnectorOut): string {
  // webhook_path is like /api/v1/connectors/{token}/inbound; join with API origin
  if (!c.webhook_path) return "";
  const origin = API_BASE.replace(/\/api\/v1$/, "");
  return `${origin}${c.webhook_path}`;
}

export default function ConnectorsPage() {
  const [items, setItems] = useState<ExternalConnectorOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState<number | undefined>();

  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const [testToken, setTestToken] = useState("");
  const [testName, setTestName] = useState("王总");
  const [testEmail, setTestEmail] = useState("wang@example.com");
  const [testPhone, setTestPhone] = useState("");
  const [testExtUid, setTestExtUid] = useState("");
  const [testMsgId, setTestMsgId] = useState("");
  const [testBody, setTestBody] = useState("我们想确认 PoC 报价和交付周期。");
  const [sending, setSending] = useState(false);
  const [testResult, setTestResult] = useState<InboundMessageResult | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    getConnectors()
      .then((r) => { setItems(r.items); setError(null); if (!testToken && r.items[0]?.webhook_token) setTestToken(r.items[0].webhook_token); })
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [testToken]);

  useEffect(() => { queueMicrotask(load); }, [load]);
  useEffect(() => { getNotificationSummary().then((s) => setUnreadCount(s.unread_count)).catch(() => {}); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true); setError(null);
    try { await createConnector({ provider: "mock", name: newName.trim() }); setNewName(""); load(); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "创建失败"); }
    finally { setCreating(false); }
  };

  const toggleStatus = async (c: ExternalConnectorOut) => {
    const next = c.status === "active" ? "paused" : "active";
    try { await updateConnector(c.id, { status: next }); load(); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "状态更新失败"); }
  };

  const copyUrl = (c: ExternalConnectorOut) => {
    const url = webhookUrl(c);
    if (url && navigator.clipboard) navigator.clipboard.writeText(url).catch(() => {});
  };

  const sendTest = async () => {
    if (!testToken || !testBody.trim()) return;
    setSending(true); setError(null); setTestResult(null);
    try {
      const res = await sendMockInboundMessage(testToken, {
        external_message_id: testMsgId.trim() || `mock-${Date.now()}`,
        sender: {
          name: testName || undefined,
          email: testEmail || undefined,
          phone: testPhone || undefined,
          external_user_id: testExtUid || undefined,
        },
        body_markdown: testBody.trim(),
        raw_payload: { provider: "mock" },
      });
      setTestResult(res);
      setTestMsgId("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "发送失败");
    } finally {
      setSending(false);
    }
  };

  return (
    <AdminShell active="connectors" unreadCount={unreadCount} eyebrow="External Connectors" title="外部渠道连接器" subtitle={`${items.length} connectors`}>
      {error && <p className="error-msg">{error}</p>}

      <section className="admin-toolbar">
        <label>新建 Mock Connector
          <input placeholder="连接器名称" value={newName} onChange={(e) => setNewName(e.target.value)} />
        </label>
        <button className="button primary" onClick={handleCreate} disabled={creating}>{creating ? "创建中..." : "新建"}</button>
      </section>

      {loading ? (
        <div className="loading-state">Loading...</div>
      ) : items.length === 0 ? (
        <div className="empty-state"><p>还没有连接器。新建一个 mock connector，即可用下方测试表单模拟外部入站消息。</p></div>
      ) : (
        <div className="connector-list">
          {items.map((c) => (
            <article className="connector-row" key={c.id}>
              <div className="connector-main">
                <strong>{c.name}</strong>
                <span className="connector-meta">
                  <span className="severity-badge">{PROVIDER_LABELS[c.provider] || c.provider}</span>
                  <span className={`stage-badge stage-${c.status === "active" ? "qualified" : "lead"}`}>{STATUS_LABELS[c.status] || c.status}</span>
                  <span>最近接收：{c.last_received_at ? new Date(c.last_received_at).toLocaleString() : "从未"}</span>
                </span>
                <code className="connector-url">{webhookUrl(c)}</code>
              </div>
              <div className="connector-actions">
                <button className="button ghost small" onClick={() => copyUrl(c)}>复制 URL</button>
                <button className="button ghost small" onClick={() => setTestToken(c.webhook_token || "")}>选为测试目标</button>
                {c.status !== "disabled" && (
                  <button className="button ghost small" onClick={() => toggleStatus(c)}>
                    {c.status === "active" ? "暂停" : "启用"}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      <section className="mock-inbound-tester">
        <div className="panel-heading"><h2>Mock 入站测试</h2></div>
        <div className="subform-grid">
          <label className="subform-full">目标连接器 (webhook token)
            <select value={testToken} onChange={(e) => setTestToken(e.target.value)}>
              <option value="">选择连接器</option>
              {items.filter((c) => c.webhook_token).map((c) => (
                <option key={c.id} value={c.webhook_token as string}>{c.name}（{STATUS_LABELS[c.status] || c.status}）</option>
              ))}
            </select>
          </label>
          <label>发件人姓名 <input value={testName} onChange={(e) => setTestName(e.target.value)} /></label>
          <label>发件人邮箱 <input value={testEmail} onChange={(e) => setTestEmail(e.target.value)} /></label>
          <label>发件人手机号 <input placeholder="飞书/企微无邮箱时用" value={testPhone} onChange={(e) => setTestPhone(e.target.value)} /></label>
          <label>external_user_id <input placeholder="平台用户 ID（可选）" value={testExtUid} onChange={(e) => setTestExtUid(e.target.value)} /></label>
          <label>external_message_id <input placeholder="留空自动生成" value={testMsgId} onChange={(e) => setTestMsgId(e.target.value)} /></label>
          <label className="subform-full">消息正文 <textarea rows={3} value={testBody} onChange={(e) => setTestBody(e.target.value)} /></label>
        </div>
        <div className="confirm-actions">
          <button className="button primary small" onClick={sendTest} disabled={sending || !testToken}>{sending ? "发送中..." : "发送测试入站"}</button>
        </div>
        {testResult && (
          <div className="mock-inbound-result">
            <p>
              {testResult.deduplicated ? "已去重（重复消息，未新建）" : "入站成功"}
              {testResult.customer && ` · 客户：${testResult.customer.name}`}
              {testResult.conversation && ` · 会话：${testResult.conversation.title}`}
            </p>
            {testResult.contact && (
              <small>
                Contact: {testResult.contact.email || "无邮箱"}
                {testResult.contact.phone && ` · ${testResult.contact.phone}`}
                {testResult.contact.external_provider && testResult.contact.external_user_id &&
                  ` · ${testResult.contact.external_provider}:${testResult.contact.external_user_id}`}
              </small>
            )}
            {testResult.message && <small>message source: {testResult.message.source}</small>}
          </div>
        )}
      </section>
    </AdminShell>
  );
}
