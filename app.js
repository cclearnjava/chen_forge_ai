const agents = [
  {
    code: "LA-01",
    name: "需求诊断 Agent",
    role: "把客户的模糊描述整理成业务目标、流程节点、风险点和 PoC 切入建议。",
    gate: "人工确认是否值得进入方案阶段",
  },
  {
    code: "SA-02",
    name: "方案架构 Agent",
    role: "生成系统边界、Agent 职责、数据流、工具权限和分阶段交付路线。",
    gate: "人工确认技术方向和安全边界",
  },
  {
    code: "PB-03",
    name: "Proposal Agent",
    role: "整理服务范围、里程碑、验收指标、报价结构和客户沟通材料。",
    gate: "人工确认报价和承诺范围",
  },
  {
    code: "FG-04",
    name: "构建 Agent",
    role: "根据批准的方案生成原型、脚本、测试清单、接口草案和部署说明。",
    gate: "人工审查代码和交付质量",
  },
  {
    code: "QA-05",
    name: "验证 Agent",
    role: "检查准确率、日志、异常路径、权限风险、回归问题和验收条件。",
    gate: "人工确认是否可以给客户试用",
  },
  {
    code: "CW-06",
    name: "案例沉淀 Agent",
    role: "把交付过程沉淀成案例、复盘、方法论和可复用的行业模板。",
    gate: "人工确认对外表达是否真实克制",
  },
  {
    code: "OP-07",
    name: "运营 Agent",
    role: "维护跟进提醒、会议纪要、待办列表、客户状态和决策摘要。",
    gate: "人工确认外部沟通内容",
  },
];

const agentGrid = document.querySelector("#agent-grid");
const leadForm = document.querySelector("#lead-form");
const briefOutput = document.querySelector("#brief-output");

function renderAgents() {
  agentGrid.innerHTML = agents
    .map(
      (agent) => `
        <article class="agent-card">
          <div>
            <span>${agent.code}</span>
            <h3>${agent.name}</h3>
            <p>${agent.role}</p>
          </div>
          <footer>${agent.gate}</footer>
        </article>
      `,
    )
    .join("");
}

leadForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(leadForm);
  const company = form.get("company");
  const problem = form.get("problem");
  const outcome = form.get("outcome");

  briefOutput.hidden = false;
  briefOutput.innerHTML = `
    <strong>初步诊断摘要</strong>
    <p><strong>目标对象：</strong>${company}</p>
    <p><strong>业务问题：</strong>${problem}</p>
    <p><strong>建议第一阶段：</strong>${outcome}</p>
    <p><strong>下一步：</strong>先确认流程输入、输出、人工审批点和成功指标，再判断是否进入 30 天 PoC。</p>
  `;
});

function startForgeMap() {
  const canvas = document.querySelector("#forge-map");
  const ctx = canvas.getContext("2d");
  const points = Array.from({ length: 26 }, (_, index) => ({
    angle: (Math.PI * 2 * index) / 26,
    radius: 120 + (index % 5) * 34,
    speed: 0.00055 + (index % 7) * 0.00008,
    size: 2 + (index % 3),
  }));

  function resize() {
    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
  }

  function draw(time) {
    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    const centerX = width * 0.63;
    const centerY = height * 0.42;
    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(49, 92, 111, 0.13)";
    ctx.lineWidth = 1;
    for (let i = 0; i < 9; i += 1) {
      ctx.beginPath();
      ctx.rect(centerX - 170 - i * 26, centerY - 118 - i * 16, 340 + i * 52, 236 + i * 32);
      ctx.stroke();
    }

    const rendered = points.map((point) => {
      const angle = point.angle + time * point.speed;
      return {
        x: centerX + Math.cos(angle) * point.radius,
        y: centerY + Math.sin(angle * 1.3) * point.radius * 0.56,
        size: point.size,
      };
    });

    ctx.strokeStyle = "rgba(184, 95, 54, 0.18)";
    rendered.forEach((point, index) => {
      for (let j = index + 1; j < rendered.length; j += 1) {
        const other = rendered[j];
        const distance = Math.hypot(point.x - other.x, point.y - other.y);
        if (distance < 145) {
          ctx.beginPath();
          ctx.moveTo(point.x, point.y);
          ctx.lineTo(other.x, other.y);
          ctx.stroke();
        }
      }
    });

    rendered.forEach((point, index) => {
      ctx.fillStyle = index % 4 === 0 ? "rgba(184, 95, 54, 0.74)" : "rgba(37, 35, 30, 0.58)";
      ctx.beginPath();
      ctx.fillRect(point.x - point.size, point.y - point.size, point.size * 2, point.size * 2);
      ctx.fill();
    });

    requestAnimationFrame(draw);
  }

  resize();
  window.addEventListener("resize", resize);
  requestAnimationFrame(draw);
}

renderAgents();
startForgeMap();
