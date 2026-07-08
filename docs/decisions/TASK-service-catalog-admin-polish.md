# TASK：Service Catalog Admin Polish 实现清单

## 背景

Service Catalog MVP 当前已经完成前后端主闭环：

```text
Service 列表
  -> 新建 Service
  -> Service 详情
  -> Package / Deliverable / Risk Rule 的新增、编辑、删除
```

从功能验收角度，这一步已经可以支持用户维护服务目录。但当前详情页的子资源管理仍然偏 MVP：

- 子资源表单字段过少。
- UI 以 inline input 为主，信息密度和可读性不足。
- 操作反馈、错误提示和删除确认还不够像正式后台。
- 前端类型仍然偏弱，部分子资源使用 `Record<string, unknown>`。
- 页面 JSX 开始变重，后续继续堆功能会降低维护性。

本任务目标是把 Service Catalog 从“能用”升级为“可运营维护”的后台模块。

## 产品目标

让 Workspace Owner 或运营人员能够稳定维护服务目录，并清楚回答：

```text
这个服务卖给谁？
有哪些服务包？
会交付什么？
哪些情况有风险？
价格、周期、排序和边界是什么？
```

完成后，Service 详情页应该像一个真正的服务产品管理台，而不是临时表单集合。

## 范围

### In Scope

- Service 详情页子资源管理体验升级。
- Package / Deliverable / Risk Rule 的结构化表单。
- 子资源前端类型强化。
- 子资源 API 返回结构优化。
- 操作状态、错误提示、删除确认。
- 页面组件化和样式整理。
- 对应后端与前端验证。

### Out of Scope

- 不做 Service Catalog 与 Knowledge Engine 的接入。
- 不做 Sales Reply Agent 使用 Service Catalog 的 Context Builder。
- 不做拖拽排序。
- 不做复杂权限系统。
- 不做多语言服务目录。
- 不做公开站点自动生成。

## 用户故事

### 用户故事 1：维护服务包

作为 Workspace Owner，我希望能为一个 Service 维护多个 Package，这样我可以表达基础版、标准版、高阶版等不同交付层级。

验收：

- 可以新增 Package。
- 可以编辑 Package。
- 可以删除 Package。
- 可以设置价格区间、周期、描述和排序。
- 删除前需要确认。
- 操作失败时只在 Package 区域提示错误。

### 用户故事 2：维护交付物

作为 Workspace Owner，我希望能维护 Service 的交付物清单，这样后续 Proposal、SOW 和报价能引用稳定交付范围。

验收：

- 可以新增 Deliverable。
- 可以编辑 Deliverable。
- 可以删除 Deliverable。
- 可以维护标题、描述、格式和排序。
- 列表中能快速看出交付物类型和摘要。

### 用户故事 3：维护风险规则

作为 Workspace Owner，我希望能维护服务风险规则，这样 Agent 在销售回复和方案生成时能避免过度承诺。

验收：

- 可以新增 Risk Rule。
- 可以编辑 Risk Rule。
- 可以删除 Risk Rule。
- 可以维护标题、描述、severity、是否 disqualify、建议回复和排序。
- 列表中 severity 有明显视觉标记。
- disqualify 规则需要比普通风险更醒目。

## 后端实现清单

### BE-1：子资源返回完整对象

当前 create/update 子资源接口需要统一返回完整对象，而不是只返回少数字段。

需要覆盖：

- `POST /admin/services/{service_id}/packages`
- `PATCH /admin/services/{service_id}/packages/{package_id}`
- `POST /admin/services/{service_id}/deliverables`
- `PATCH /admin/services/{service_id}/deliverables/{deliverable_id}`
- `POST /admin/services/{service_id}/risk-rules`
- `PATCH /admin/services/{service_id}/risk-rules/{rule_id}`

Package 返回字段：

```text
id
service_id
workspace_id
name
description
price_min
price_max
currency
duration
sort_order
is_active
created_at
updated_at
```

Deliverable 返回字段：

```text
id
service_id
workspace_id
package_id
title
description
format
sort_order
created_at
updated_at
```

Risk Rule 返回字段：

```text
id
service_id
workspace_id
title
description
severity
disqualifies
suggested_response
sort_order
created_at
updated_at
```

### BE-2：补充 schema 或序列化 helper

避免在 route 里手写零散 dict。

可选方案：

- 使用 Pydantic schema。
- 或先使用 `_package_to_dict`、`_deliverable_to_dict`、`_risk_rule_to_dict` helper。

MVP polish 阶段建议先用 helper，保持改动小。

### BE-3：请求字段校验

最低要求：

- Package `name` 必填。
- Deliverable `title` 必填。
- Risk Rule `title` 必填。
- Risk Rule `severity` 只能是 `low | medium | high | critical`。
- `price_min`、`price_max`、`sort_order` 不能是非法类型。

### BE-4：后端测试补充

新增或扩展 `backend/tests/test_service_catalog.py`：

- create package 返回完整字段。
- update package 返回完整字段。
- create deliverable 返回完整字段。
- update deliverable 返回完整字段。
- create risk rule 返回完整字段。
- update risk rule 返回完整字段。
- invalid risk severity 返回 422 或 400。
- 跨 workspace 子资源不可读、不可改、不可删。

## 前端实现清单

### FE-1：前端类型定义

在 `frontend/src/lib/admin-api.ts` 增加明确类型：

```ts
export interface ServicePackageOut {}
export interface ServiceDeliverableOut {}
export interface ServiceRiskRuleOut {}
```

替换当前详情页里的：

```ts
Record<string, unknown>[]
```

目标：

- 不再使用 `String(p.name)` 这类兜底式读取。
- API client 返回类型稳定。
- 详情页组件 props 可读。

### FE-2：API client 返回类型升级

更新这些函数的返回类型：

- `getServicePackages`
- `createServicePackage`
- `updateServicePackage`
- `deleteServicePackage`
- `getServiceDeliverables`
- `createServiceDeliverable`
- `updateServiceDeliverable`
- `deleteServiceDeliverable`
- `getServiceRiskRules`
- `createServiceRiskRule`
- `updateServiceRiskRule`
- `deleteServiceRiskRule`

### FE-3：抽取子资源 Panel 组件

新增组件建议路径：

```text
frontend/src/components/admin/service-catalog/service-sub-resource-panel.tsx
```

组件职责：

- 标题和说明。
- 列表渲染。
- 空状态。
- 新增入口。
- 编辑入口。
- 删除确认。
- loading / saving / deleting 状态。
- panel 内错误提示。

### FE-4：抽取三类表单组件

建议路径：

```text
frontend/src/components/admin/service-catalog/service-package-form.tsx
frontend/src/components/admin/service-catalog/service-deliverable-form.tsx
frontend/src/components/admin/service-catalog/service-risk-rule-form.tsx
```

Package 表单字段：

- name
- description
- price_min
- price_max
- duration
- currency
- sort_order

Deliverable 表单字段：

- title
- description
- format
- sort_order

Risk Rule 表单字段：

- title
- description
- severity
- disqualifies
- suggested_response
- sort_order

### FE-5：新增和编辑体验

推荐使用展开式编辑区，不使用全局 modal。

原因：

- 当前后台页面结构简单。
- 子资源数量不会特别大。
- 展开式编辑不会打断上下文。

交互要求：

- 点击新增，展开空表单。
- 点击编辑，展开当前资源表单。
- 保存中按钮 disabled。
- 保存成功后刷新对应列表。
- 取消编辑恢复原列表。
- 表单基础校验失败时不发请求。

### FE-6：删除确认

删除前必须二次确认。

MVP polish 可以使用内联确认：

```text
删除 -> 确认删除 / 取消
```

不要求浏览器 `confirm`，也不建议直接一键删除。

### FE-7：列表展示升级

Package 列表展示：

- name
- description 摘要
- price range
- duration
- sort_order

Deliverable 列表展示：

- title
- format
- description 摘要
- sort_order

Risk Rule 列表展示：

- title
- severity badge
- disqualifies badge
- suggested_response 摘要
- sort_order

### FE-8：Service 详情摘要区

详情页顶部增加摘要区：

- status
- price range
- duration
- risk notes
- updated_at

目标是用户进入详情页后，不用滚动就知道该服务当前是否可售、价格范围和主要风险。

### FE-9：文案统一

当前页面存在中英文混用。建议后台统一中文：

```text
新增
编辑
保存
取消
删除
确认删除
服务包
交付物
风险规则
```

技术字段如 `slug`、`currency` 可以保留英文。

### FE-10：样式整理

移除详情页里的 inline style。

新增或扩展 CSS class：

```text
subresource-panel
subresource-list
subresource-item
subresource-actions
subresource-form
service-summary
severity-badge
confirm-actions
```

## UI 结构建议

Service 详情页建议结构：

```text
Service Header
  - 返回列表
  - 状态 badge
  - 激活 / 停用 / 归档

Service Summary
  - 价格区间
  - 周期
  - 风险提示
  - 更新时间

Basic Info
  - 定位
  - 目标客户
  - 痛点
  - 结果

Sub Resource Tabs or Panels
  - 服务包 Packages
  - 交付物 Deliverables
  - 风险规则 Risk Rules
```

如果当前 CSS 成本较低，可以先使用三个并列 panel；如果移动端显示拥挤，再切换成 tabs。

## 验收标准

### 产品验收

- 用户可以完整维护一个 Service 的服务包、交付物和风险规则。
- 用户能从详情页快速判断服务是否可售。
- 用户删除任何子资源前都有确认。
- 用户操作失败时知道哪个区域失败。
- 页面文案统一、信息结构清晰。

### 后端验收

- 子资源 create/update 返回完整对象。
- 子资源字段有基础校验。
- 子资源 workspace 隔离有效。
- `backend/tests/test_service_catalog.py` 通过。
- 后端全量测试通过。

### 前端验收

- Service 详情页不再使用 `Record<string, unknown>[]` 管理子资源。
- 子资源新增、编辑、删除都有 loading / error / cancel 状态。
- 页面无明显 inline style 堆积。
- `npm run lint` 通过。
- `npm run build` 通过。

## 推荐实现顺序

### Step 1：后端返回结构稳定化

先统一子资源返回完整对象，并补测试。

原因：

- 前端类型依赖稳定 API。
- 如果后端返回不完整，前端组件会继续堆兜底逻辑。

### Step 2：前端类型和 API client

增加三类子资源类型，替换弱类型。

### Step 3：抽组件

从详情页抽出 panel 和 form，降低页面复杂度。

### Step 4：结构化表单

补齐字段，让服务目录真正可运营维护。

### Step 5：交互状态和删除确认

补 saving、deleting、error、confirm。

### Step 6：视觉 polish

统一文案、badge、summary、CSS class。

## 不建议现在做的事

- 不建议马上做拖拽排序。
- 不建议引入大型 UI 组件库。
- 不建议做复杂 modal 系统。
- 不建议把 Service Catalog 和 Agent 逻辑混在这一步。
- 不建议为了 polish 大规模重构 AdminShell。

## 完成定义

当以下条件全部满足时，本任务完成：

```text
1. 子资源 API 返回完整对象。
2. 子资源前端类型明确。
3. Service 详情页可以结构化新增、编辑、删除三类子资源。
4. 删除有确认。
5. 操作有局部 loading/error 反馈。
6. 页面文案和样式统一。
7. 前端 lint 通过。
8. 前端 build 通过。
9. Service Catalog 专项测试通过。
10. 后端全量测试通过。
```

