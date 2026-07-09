"use client";

import { useState, type ReactNode } from "react";

interface Props<T, D> {
  title: string;
  addLabel: string;
  items: T[];
  emptyDraft: D;
  getId: (item: T) => string;
  getLabel: (item: T) => string;
  toDraft: (item: T) => D;
  isValid: (draft: D) => boolean;
  renderItem: (item: T) => ReactNode;
  renderForm: (draft: D, set: (patch: Partial<D>) => void) => ReactNode;
  onCreate: (draft: D) => Promise<void>;
  onUpdate: (id: string, draft: D) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export default function ServiceSubResourcePanel<T, D>(props: Props<T, D>) {
  const [adding, setAdding] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [draft, setDraft] = useState<D>(props.emptyDraft);
  const [confirmDel, setConfirmDel] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const set = (patch: Partial<D>) => setDraft((d) => ({ ...d, ...patch }));
  const startAdd = () => { setDraft(props.emptyDraft); setEditId(null); setConfirmDel(null); setAdding(true); setError(null); };
  const startEdit = (item: T) => { setDraft(props.toDraft(item)); setAdding(false); setConfirmDel(null); setEditId(props.getId(item)); setError(null); };
  const cancel = () => { setAdding(false); setEditId(null); setError(null); };

  const submit = async () => {
    if (!props.isValid(draft)) { setError("请填写必填字段"); return; }
    setSaving(true); setError(null);
    try {
      if (editId) await props.onUpdate(editId, draft);
      else await props.onCreate(draft);
      cancel();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: string) => {
    setDeleting(id); setError(null);
    try {
      await props.onDelete(id);
      setConfirmDel(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setDeleting(null);
    }
  };

  const formOpen = adding || editId !== null;

  return (
    <article className="subresource-panel">
      <div className="panel-heading">
        <h2>{props.title}</h2>
        {!formOpen && (
          <button className="button primary small" onClick={startAdd}>{props.addLabel}</button>
        )}
      </div>

      {error && <p className="error-msg">{error}</p>}

      {formOpen && (
        <div className="subresource-form">
          {props.renderForm(draft, set)}
          <div className="confirm-actions">
            <button className="button primary small" onClick={submit} disabled={saving}>{saving ? "保存中..." : "保存"}</button>
            <button className="button ghost small" onClick={cancel} disabled={saving}>取消</button>
          </div>
        </div>
      )}

      <div className="subresource-list">
        {props.items.length === 0 && !formOpen && <p className="subresource-empty">暂无数据</p>}
        {props.items.map((item) => {
          const id = props.getId(item);
          if (confirmDel === id) {
            return (
              <div key={id} className="subresource-item">
                <span className="confirm-actions">
                  确认删除「{props.getLabel(item)}」？
                  <button className="button primary small" onClick={() => remove(id)} disabled={deleting === id}>{deleting === id ? "删除中..." : "确认删除"}</button>
                  <button className="button ghost small" onClick={() => setConfirmDel(null)} disabled={deleting === id}>取消</button>
                </span>
              </div>
            );
          }
          return (
            <div key={id} className="subresource-item">
              <div className="subresource-body">{props.renderItem(item)}</div>
              <span className="subresource-actions">
                <button className="button ghost small" onClick={() => startEdit(item)} disabled={formOpen}>编辑</button>
                <button className="button ghost small" onClick={() => setConfirmDel(id)} disabled={formOpen}>删除</button>
              </span>
            </div>
          );
        })}
      </div>
    </article>
  );
}
