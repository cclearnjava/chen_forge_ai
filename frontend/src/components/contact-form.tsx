"use client";

import { useState, type FormEvent } from "react";

const OUTCOMES = [
  "AI Agent 流程诊断与蓝图",
  "企业知识库 / RAG 问答",
  "ChatBI / 自然语言问数",
  "内部自动化 MVP",
];

export default function ContactForm() {
  const [brief, setBrief] = useState<{
    company: string;
    problem: string;
    outcome: string;
  } | null>(null);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBrief({
      company: (form.get("company") as string) || "",
      problem: (form.get("problem") as string) || "",
      outcome: (form.get("outcome") as string) || "",
    });
  }

  return (
    <section className="section contact-section" id="contact">
      <div>
        <div className="section-heading">
          <p className="eyebrow">Start with one workflow</p>
          <h2>先提交一个业务问题，我会判断它是否适合做 AI Agent PoC。</h2>
          <p className="section-note" style={{ marginTop: 16 }}>
            不需要准备完整需求文档。描述一个你觉得耗人、重复、难追踪或响应慢的流程即可。
          </p>
        </div>
        <form className="lead-form" onSubmit={handleSubmit}>
          <label>
            公司或项目
            <input
              name="company"
              autoComplete="organization"
              placeholder="例如：区域连锁门店 / SaaS 团队 / 制造企业"
              required
            />
          </label>
          <label>
            想解决的问题
            <textarea
              name="problem"
              rows={4}
              placeholder="例如：客服重复问答太多、销售资料整理慢、运营日报靠人工、老板想直接问数据..."
              required
            />
          </label>
          <label>
            期望第一阶段结果
            <select name="outcome" required defaultValue="">
              <option value="" disabled>请选择</option>
              {OUTCOMES.map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
          </label>
          <button className="button primary" type="submit">
            生成初步诊断摘要
          </button>
        </form>
      </div>

      {brief && (
        <div className="brief-output">
          <strong>初步诊断摘要</strong>
          <p><strong>目标对象：</strong>{brief.company}</p>
          <p><strong>业务问题：</strong>{brief.problem}</p>
          <p><strong>建议第一阶段：</strong>{brief.outcome}</p>
          <p>
            <strong>下一步：</strong>
            先确认流程输入、输出、人工审批点和成功指标，再判断是否进入 30 天 PoC。
          </p>
        </div>
      )}
    </section>
  );
}
