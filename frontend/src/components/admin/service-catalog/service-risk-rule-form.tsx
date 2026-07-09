"use client";

export interface RiskRuleDraft {
  title: string;
  description: string;
  severity: string;
  disqualifies: boolean;
  suggested_response: string;
  sort_order: string;
}

export const emptyRiskRuleDraft: RiskRuleDraft = {
  title: "", description: "", severity: "medium", disqualifies: false, suggested_response: "", sort_order: "0",
};

export default function ServiceRiskRuleForm({
  draft, set,
}: { draft: RiskRuleDraft; set: (patch: Partial<RiskRuleDraft>) => void }) {
  return (
    <div className="subform-grid">
      <label className="subform-full">标题 *
        <input value={draft.title} onChange={(e) => set({ title: e.target.value })} placeholder="如：数据合规风险" />
      </label>
      <label className="subform-full">描述
        <textarea value={draft.description} rows={2} onChange={(e) => set({ description: e.target.value })} />
      </label>
      <label>严重程度
        <select value={draft.severity} onChange={(e) => set({ severity: e.target.value })}>
          <option value="low">低</option>
          <option value="medium">中</option>
          <option value="high">高</option>
          <option value="critical">严重</option>
        </select>
      </label>
      <label>排序
        <input type="number" value={draft.sort_order} onChange={(e) => set({ sort_order: e.target.value })} />
      </label>
      <label className="subform-full subform-checkbox">
        <input type="checkbox" checked={draft.disqualifies} onChange={(e) => set({ disqualifies: e.target.checked })} />
        命中即不建议承接
      </label>
      <label className="subform-full">建议回复
        <textarea value={draft.suggested_response} rows={2} onChange={(e) => set({ suggested_response: e.target.value })} />
      </label>
    </div>
  );
}
