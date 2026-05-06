

## 第1章

### 图1-1 技术路线图

```text
Create a publication-ready BioRender-enhanced academic overview figure for a journal paper. White background, flat vector graphics, thin outlines, clear spacing, muted 3-color palette, sans-serif font. All visible text inside the figure must be Simplified Chinese only. Do not render any English words inside the image. Do not invent any information beyond the thesis. Research object: the technical route and research positioning of a mining hot-work safety monitoring system. Logical structure: divide the figure into two clearly separated zones. In the first zone, show a linear technical route with five equal-height rounded boxes connected by one-way arrows, with the Chinese stage labels “问题与规范约束”, “统一视觉感知”, “几何/时序/身份判定”, “边缘—云端系统”, and “实验与系统验证”. In the second zone, show a two-dimensional positioning map with the horizontal axis labeled “单任务检测” to “多任务协同感知” and the vertical axis labeled “算法模块” to “规范映射与可部署系统”. Add 3 to 5 neutral reference points such as “火焰单任务”, “安全帽单任务”, and “通用云边系统”, and highlight “本文” in the upper-right collaborative and deployable region. Key conclusion to emphasize: this work moves from single-task algorithmic detection toward a deployable, standards-aware, multi-task edge-cloud safety monitoring system. Keep the two zones parallel rather than causal, with a clean divider and a small legend in Chinese only.
```

---

## 第2章
2-1系统总体架构图

端-前-后

### 图2-2 系统功能结构图

```text
Create a publication-ready BioRender-enhanced system function structure figure for a journal paper. White background, vector style, muted 4-color palette, sans-serif font, minimal shadows, strict alignment. All visible text inside the figure must be Simplified Chinese only. Do not display any English words in the image. Research object: a safety monitoring system for mining hot-work operations. Logical structure: a three-level hierarchical function structure, not a workflow. At the top center place one rounded main box labeled “矿业动火作业安全监测系统”. Below it, split the figure into two major zones labeled “边缘检测与告警子系统” and “云端管理与展示子系统”. Under the edge-side zone, place the modules “视频采集”, “多目标检测”, “气瓶测距”, “火焰/安全帽/人脸判定”, “低照度增强”, “规则引擎”, “本地声光告警”, and “告警上报”. Under the cloud-side zone, place the modules “设备管理”, “告警接收与存储”, “用户与任务管理”, “视频流协调”, “Web看板展示”, and “告警确认与统计”. Use only a very small number of simple connectors, and show that “告警上报” is linked to the cloud side. Key conclusion to emphasize: the system adopts a modular edge-cloud collaborative architecture in which the edge side performs on-site video access, AI analysis, and local alerting, while the cloud side performs management, storage, visualization, and confirmation statistics.
```

### 图2-3 系统逻辑架构图

```text
Create a publication-ready BioRender-enhanced logical architecture and data-flow figure for a journal paper. White background, clean vector layout, muted 3 to 4 academic colors, sans-serif Chinese font. All visible text inside the figure must be Simplified Chinese only. Do not render any English words in the image. Research object: the closed-loop monitoring logic of the mining hot-work safety monitoring system. Logical structure: build one clear main chain from left to right with Chinese labels “视频输入” → “预处理” → “统一目标检测” → “安全规则引擎” → “安全事件” → split into “本地声光告警” and “云端上报” → “管理端展示与确认”. Near “预处理”, mark “可选低照度增强”. Around or beneath “安全规则引擎”, add four supporting branches in Chinese only: “气瓶间距判定”, “火焰/火星/烟雾多帧判定”, “安全帽相关判定”, and “人脸授权判定”. Separate “边缘侧” and “云端侧” with a soft boundary box. If authentication is shown, label it in Chinese only as “设备令牌认证” and “用户令牌认证”, without English protocol strings. Key conclusion to emphasize: the system forms a complete closed loop from video acquisition to intelligent analysis, rule-based decision, alert generation, cloud reporting, and management-side confirmation.
```

### 图2-4 边缘检测与告警子系统结构图

```text
Create a publication-ready BioRender-enhanced subsystem architecture figure for a journal paper. White background, muted palette, clean layering, thin outlines, sans-serif Chinese font. All visible text inside the figure must be Simplified Chinese only. Research object: the edge-side detection and alert subsystem deployed on the on-site AI edge node. Logical structure: organize the figure into four clear layered bands labeled “表示层”, “核心逻辑层”, “业务逻辑层”, and “工具层”. In “表示层”, include “主界面” and “配置与日志”. In “核心逻辑层”, include “检测器”, “人脸识别器”, “告警上传线程”, and optionally “视频推流模块”. In “业务逻辑层”, include “安全规则引擎” and “距离估计器”. In “工具层”, include “相机标定” and “低照度增强”. Show simple internal arrows indicating that video and detection results move downward or across toward the rule engine, and that alerts are finally sent to upload and local warning. Key conclusion to emphasize: the edge subsystem concentrates real-time perception, local decision-making, and low-latency alerting on a single on-site AI node, with the rule engine as the decision center.
```

### 图2-5 后端子系统结构图

2-6 数据库核心E-R图

### 图2-7前端子系统结构图

```text
Create a publication-ready BioRender-enhanced internal cloud interface and data-flow figure for a journal paper. White background, precise vector layout, 3 to 4 muted colors, sans-serif Chinese font. All visible text inside the figure must be Simplified Chinese only. Research object: the internal calling relationships inside the cloud subsystem. Logical structure: show a layered path from “浏览器端” to “接口层” to “服务层” to “数据层”. In the browser layer, include Chinese labels for the management pages. In the interface layer, include grouped interfaces for “认证”, “设备”, “告警”, “任务”, and “视频流”. In the service layer, show business processing modules. In the data layer, show persistence for “用户”, “设备”, “告警”, and “任务”. Connect the layers with a clean top-down or left-right flow, making clear that the browser side only accesses the interface layer rather than the database directly. Key conclusion to emphasize: the cloud subsystem follows a clear layered design in which front-end calls enter through a unified interface layer, are processed in service modules, and are finally persisted in the data layer.
```

### 图2-8 安全事件生成与告警闭环流程图

```text
Create a publication-ready BioRender-enhanced safety-rule and alert-linkage logic figure for a journal paper. White background, highly organized three-column layout, limited alert colors used sparingly, sans-serif Chinese font. All visible text inside the figure must be Simplified Chinese only. Research object: the rule-based mapping from safety events to alert actions. Logical structure: divide the figure into three columns labeled “输入事件”, “规则映射”, and “告警动作”. In the left column, include Chinese event categories corresponding to the thesis, such as “气瓶距离违规”, “火焰”, “烟雾”, “安全帽未佩戴”, and “非授权闯入”, with small fields like “等级”, “时间”, and “设备”. In the middle column, show a compact rule engine block with severity mapping and trigger conditions, using Chinese-only severity labels if needed such as “高”, “中”, “低” instead of English. In the right column, include “本地声光告警”, “上传云端”, and “管理端展示与确认”. Key conclusion to emphasize: heterogeneous perception outputs are unified into structured safety events and then transformed by a rule engine into coordinated local and cloud alert actions.
```

### 图2-9 所有接口结构框图
```
前后端、边缘端所有接口绘制在一张图
---

## 第3章

### 图3-1 YOLO统一检测模型结构示意图

```text
Create a publication-ready BioRender-enhanced model-architecture figure for a journal paper. White background, vector blocks, clean academic spacing, muted colors, sans-serif Chinese font. All visible text inside the figure must be Simplified Chinese only. Mathematical symbols may be used only if necessary, but no English words should appear in visible labels. Research object: the unified single-stage detection model used for multiple safety targets in mining hot-work scenes. Logical structure: arrange the figure from left to right as “输入图像” → “主干网络” → “特征融合” → “检测头” → “多尺度输出”. Show multiple scale feature maps as stacked blocks, and show output examples as “边界框”, “类别”, and “置信度”. Below or near the output, show the Chinese class names “人脸”, “火焰”, “烟雾”, “火星”, “气瓶”, “安全帽”, and “未戴安全帽”. Key conclusion to emphasize: one unified detector performs multi-class collaborative perception in a single forward pass and directly supports downstream distance estimation, flame confirmation, helmet judgment, and face-related processing.
```

### 图3-2 针孔模型与单目测距几何关系

```text
跳过
```

### 图3-3 火焰多帧一致性判定流程图

```text
Create a publication-ready BioRender-enhanced flow figure for a journal paper. White background, compact process layout, muted colors, clean arrows, sans-serif Chinese font. All visible text inside the figure must be Simplified Chinese only. Research object: multi-frame consistency confirmation of flame and related hazardous phenomena. Logical structure: build a clear flow with the Chinese nodes “当前帧检测” → “置信度≥阈值？” → yes branch “计数加一” and no branch “计数清零” → “计数≥N？” → yes branch “上报告警” and no branch “不告警”. Optionally add a small side timeline in Chinese only to show that isolated high-confidence frames are rejected while consecutive high-confidence frames are accepted. Key conclusion to emphasize: the system suppresses single-frame false alarms and triggers flame-related alerts only when the confidence condition remains satisfied across consecutive frames.
```

### 图3-4 人脸授权与闯入检测流程图

```text
Create a publication-ready BioRender-enhanced identity-verification flow figure for a journal paper. White background, clean process blocks, vector style, muted academic palette, sans-serif Chinese font. All visible text inside the figure must be Simplified Chinese only. Mathematical symbols such as θ may appear only if needed, but no English words should appear in visible labels. Research object: authorized face verification and intrusion warning in the mining hot-work safety system. Logical structure: build a left-to-right or top-to-bottom flow with the Chinese steps “人员检测” → “人脸裁剪” → “特征提取” → “与授权库比对” → “相似度≥阈值？” → yes branch “授权通过” and no branch “非授权闯入告警”. Optionally add a small annotation in Chinese explaining that the comparison is based on feature similarity. Key conclusion to emphasize: the system identifies authorized personnel by face-feature matching and converts failed authorization into a direct intrusion alert event.
```

