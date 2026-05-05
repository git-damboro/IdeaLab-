# 概念结构设计（E-R图）Mermaid 草图

为保证图面更清晰、整体更方正，建议将概念结构设计拆成 3 张小 E-R 图，分别对应用户侧个性化管理、文献检索与知识服务、后台管理与权限任务。

### 1. 用户侧个性化管理 E-R 图

#### 图名

图4.X 用户侧个性化管理概念结构设计图

#### Mermaid 草图

```mermaid
%%{init: {
  "flowchart": { "curve": "linear" },
  "themeVariables": {
    "fontFamily": "Microsoft YaHei, SimSun, sans-serif",
    "fontSize": "16px"
  }
}}%%
flowchart TB

  U[用户]
  F[收藏夹]
  FV[收藏记录]
  N[用户笔记]
  H[搜索历史]
  P[文献]

  R1{拥有}
  R2{收藏}
  R3{编写}
  R4{记录}
  R5{关联}

  U ---|1| R1
  R1 ---|n| F

  U ---|1| R2
  R2 ---|n| FV
  F ---|1| R2
  P ---|1| R2

  U ---|1| R3
  R3 ---|n| N
  P ---|1| R5
  R5 ---|n| N

  U ---|1| R4
  R4 ---|n| H

  U1([user_id]) --- U
  U2([用户名]) --- U
  U3([密码哈希]) --- U
  U4([状态]) --- U

  F1([folder_id]) --- F
  F2([名称]) --- F
  F3([创建时间]) --- F

  FV1([favorite_id]) --- FV
  FV2([收藏时间]) --- FV

  N1([note_id]) --- N
  N2([内容]) --- N
  N3([更新时间]) --- N

  H1([history_id]) --- H
  H2([查询词]) --- H
  H3([检索时间]) --- H

  P1([paper_id]) --- P
  P2([标题]) --- P
  P3([年份]) --- P

  subgraph ROW1[" "]
    direction LR
    F
    R1
    U
    R4
    H
  end

  subgraph ROW2[" "]
    direction LR
    FV
    R2
    P
    R5
    N
  end

  style ROW1 fill:none,stroke:none
  style ROW2 fill:none,stroke:none
```

### 2. 文献检索与知识服务 E-R 图

#### 图名

图4.X 文献检索与知识服务概念结构设计图

#### Mermaid 草图

```mermaid
%%{init: {
  "flowchart": { "curve": "linear" },
  "themeVariables": {
    "fontFamily": "Microsoft YaHei, SimSun, sans-serif",
    "fontSize": "16px"
  }
}}%%
flowchart TB

  P[文献]
  C[摘要缓存]
  V[向量索引]
  H[搜索历史]
  U[用户]

  R1{生成}
  R2{建立}
  R3{检索}

  P ---|1| R1
  R1 ---|n| C

  P ---|1| R2
  R2 ---|1| V

  U ---|1| R3
  R3 ---|n| H
  P ---|n| R3

  P1([paper_id]) --- P
  P2([标题]) --- P
  P3([作者]) --- P
  P4([年份]) --- P
  P5([状态]) --- P

  C1([cache_id]) --- C
  C2([查询词]) --- C
  C3([摘要内容]) --- C

  V1([paper_id]) --- V
  V2([向量维度]) --- V
  V3([相似度检索]) --- V

  H1([history_id]) --- H
  H2([查询词]) --- H
  H3([检索时间]) --- H

  U1([user_id]) --- U
  U2([用户名]) --- U

  subgraph ROW1[" "]
    direction LR
    C
    R1
    P
    R2
    V
  end

  subgraph ROW2[" "]
    direction LR
    U
    R3
    H
  end

  style ROW1 fill:none,stroke:none
  style ROW2 fill:none,stroke:none
```

### 3. 后台管理与权限任务 E-R 图

#### 图名

图4.X 后台管理与权限任务概念结构设计图

#### Mermaid 草图

```mermaid
%%{init: {
  "flowchart": { "curve": "linear" },
  "themeVariables": {
    "fontFamily": "Microsoft YaHei, SimSun, sans-serif",
    "fontSize": "16px"
  }
}}%%
flowchart TB

  U[用户]
  R[角色]
  PM[权限]
  J[导入任务]
  A[审计日志]
  P[文献]

  R1{拥有}
  R2{授予}
  R3{导入}
  R4{记录}

  U ---|n| R1
  R1 ---|n| R

  R ---|n| R2
  R2 ---|n| PM

  J ---|1| R3
  R3 ---|n| P

  U ---|1| R4
  R4 ---|n| A
  J ---|1| R4

  U1([user_id]) --- U
  U2([用户名]) --- U
  U3([状态]) --- U

  R11([role_code]) --- R
  R12([角色名]) --- R

  PM1([perm_code]) --- PM
  PM2([权限名]) --- PM

  J1([job_id]) --- J
  J2([任务类型]) --- J
  J3([任务状态]) --- J
  J4([进度]) --- J

  A1([log_id]) --- A
  A2([动作]) --- A
  A3([时间]) --- A

  P1([paper_id]) --- P
  P2([标题]) --- P
  P3([状态]) --- P

  subgraph ROW1[" "]
    direction LR
    U
    R1
    R
    R2
    PM
  end

  subgraph ROW2[" "]
    direction LR
    J
    R3
    P
    R4
    A
  end

  style ROW1 fill:none,stroke:none
  style ROW2 fill:none,stroke:none
```
 


 ```mermaid
flowchart TB
  A[进入系统] --> B{选择操作}

  B -->|注册| C[填写注册信息]
  B -->|登录| D[填写账号密码]

  C --> E{信息是否合法}
  E -->|否| C1[提示并重新填写]
  C1 --> C
  E -->|是| F{用户名是否存在}
  F -->|是| F1[提示用户名已存在]
  F1 --> C
  F -->|否| G[创建用户]
  G --> H[注册成功]
  H --> D

  D --> I{账号密码是否正确}
  I -->|否| I1[提示登录失败]
  I1 --> D
  I -->|是| J[生成Token]
  J --> K[进入首页]

```