"use client";

export interface DeliverableDraft {
  title: string;
  description: string;
  format: string;
  sort_order: string;
}

export const emptyDeliverableDraft: DeliverableDraft = {
  title: "", description: "", format: "", sort_order: "0",
};

export default function ServiceDeliverableForm({
  draft, set,
}: { draft: DeliverableDraft; set: (patch: Partial<DeliverableDraft>) => void }) {
  return (
    <div className="subform-grid">
      <label className="subform-full">标题 *
        <input value={draft.title} onChange={(e) => set({ title: e.target.value })} placeholder="如：技术方案文档" />
      </label>
      <label className="subform-full">描述
        <textarea value={draft.description} rows={2} onChange={(e) => set({ description: e.target.value })} />
      </label>
      <label>格式
        <input value={draft.format} onChange={(e) => set({ format: e.target.value })} placeholder="如：PDF / 源码 / 演示" />
      </label>
      <label>排序
        <input type="number" value={draft.sort_order} onChange={(e) => set({ sort_order: e.target.value })} />
      </label>
    </div>
  );
}
