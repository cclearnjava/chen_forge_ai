"use client";

export interface PackageDraft {
  name: string;
  description: string;
  price_min: string;
  price_max: string;
  duration: string;
  currency: string;
  sort_order: string;
}

export const emptyPackageDraft: PackageDraft = {
  name: "", description: "", price_min: "", price_max: "", duration: "", currency: "CNY", sort_order: "0",
};

export default function ServicePackageForm({
  draft, set,
}: { draft: PackageDraft; set: (patch: Partial<PackageDraft>) => void }) {
  return (
    <div className="subform-grid">
      <label className="subform-full">名称 *
        <input value={draft.name} onChange={(e) => set({ name: e.target.value })} placeholder="如：标准版" />
      </label>
      <label className="subform-full">描述
        <textarea value={draft.description} rows={2} onChange={(e) => set({ description: e.target.value })} />
      </label>
      <label>最低价 (CNY)
        <input type="number" value={draft.price_min} onChange={(e) => set({ price_min: e.target.value })} />
      </label>
      <label>最高价 (CNY)
        <input type="number" value={draft.price_max} onChange={(e) => set({ price_max: e.target.value })} />
      </label>
      <label>周期
        <input value={draft.duration} onChange={(e) => set({ duration: e.target.value })} placeholder="如：4-6 周" />
      </label>
      <label>currency
        <input value={draft.currency} onChange={(e) => set({ currency: e.target.value })} />
      </label>
      <label>排序
        <input type="number" value={draft.sort_order} onChange={(e) => set({ sort_order: e.target.value })} />
      </label>
    </div>
  );
}
