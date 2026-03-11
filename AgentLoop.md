# OpenCode 连续性思考实现原理分析

## 核心发现

### 1. 关键机制：基于 `finish_reason` 的循环

OpenCode **不是通过"判断回答是否满足用户需求"** 来决定是否继续，而是采用 **ReAct (Reasoning + Acting)** 模式：

**核心循环在 `session/prompt.ts:295-326`**：

```typescript
while (true) {
  // ... 处理消息

  // 退出条件判断
  if (
    lastAssistant?.finish &&
    !["tool-calls", "unknown"].includes(lastAssistant.finish) &&
    lastUser.id < lastAssistant.id
  ) {
    break; // 退出循环
  }

  // 继续处理...
}
```

### 2. `finish_reason` 决定是否继续

| finish_reason | 行为     | 含义                               |
| ------------- | -------- | ---------------------------------- |
| `tool-calls`  | 继续循环 | 模型调用了工具，需要执行后返回结果 |
| `unknown`     | 继续循环 | 未知原因，继续尝试                 |
| `stop`        | 退出循环 | 模型认为任务完成                   |
| `end-turn`    | 退出循环 | 回合结束                           |
| `length`      | 退出循环 | 达到token限制                      |

### 3. 处理器返回值 (`processor.ts:420-423`)

```typescript
if (needsCompaction) return "compact"; // 需要压缩上下文
if (blocked) return "stop"; // 权限被拒绝
if (input.assistantMessage.error) return "stop"; // 有错误
return "continue"; // 继续循环
```

---

## 实现方案

### 方案一：简单版（基于 finish_reason）

```typescript
async function agentLoop(userMessage: string) {
  const messages = [{ role: "user", content: userMessage }];

  while (true) {
    const response = await llm.chat({
      messages,
      tools: availableTools,
    });

    // 检查 finish_reason
    if (response.finish_reason !== "tool_calls") {
      return response.content; // 任务完成，退出
    }

    // 执行工具调用
    for (const toolCall of response.tool_calls) {
      const result = await executeTool(toolCall.name, toolCall.arguments);
      messages.push({
        role: "tool",
        tool_call_id: toolCall.id,
        content: JSON.stringify(result),
      });
    }

    // 添加助手消息
    messages.push({
      role: "assistant",
      content: response.content,
      tool_calls: response.tool_calls,
    });
  }
}
```

### 方案二：增强版（加入状态管理和错误处理）

```typescript
type LoopResult = "continue" | "stop" | "compact" | "error";

async function agentLoop(input: {
  sessionID: string;
  userMessage: Message;
  tools: Record<string, Tool>;
  maxSteps: number;
  abort: AbortSignal;
}) {
  let step = 0;

  while (true) {
    if (input.abort.aborted) return { status: "aborted" };
    if (step >= input.maxSteps) return { status: "max_steps" };

    step++;

    const response = await streamLLM({
      messages: getHistory(input.sessionID),
      tools: input.tools,
      abort: input.abort,
    });

    // 处理流式响应
    for await (const chunk of response.stream) {
      // 更新UI，显示思考过程
      await updateUI(chunk);
    }

    // 判断下一步
    const result = await processResponse(response);

    switch (result) {
      case "continue":
        continue; // 继续循环
      case "stop":
        return { status: "completed" };
      case "compact":
        await compactContext(input.sessionID);
        continue;
      case "error":
        return { status: "error", error: response.error };
    }
  }
}

async function processResponse(response: LLMResponse): Promise<LoopResult> {
  // 1. 有错误
  if (response.error) return "error";

  // 2. 需要压缩上下文
  if (isContextOverflow(response.usage)) return "compact";

  // 3. finish_reason 判断
  const finish = response.finish_reason;

  if (finish === "tool_calls") {
    // 执行工具
    await executeTools(response.tool_calls);
    return "continue";
  }

  if (["stop", "end_turn"].includes(finish)) {
    return "stop";
  }

  return "continue";
}
```

### 方案三：完整版（参考 OpenCode 架构）

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Loop                              │
├─────────────────────────────────────────────────────────────┤
│  1. 用户发送消息                                              │
│      ↓                                                       │
│  2. 创建 User Message，存储到 Session                         │
│      ↓                                                       │
│  3. Loop 开始                                                │
│      ├─ 检查：上一次 assistant.finish == "stop"? → 退出       │
│      ├─ 检查：上下文溢出? → 触发压缩                           │
│      ├─ 检查：有待处理的 subtask? → 执行子任务                 │
│      ↓                                                       │
│  4. 调用 LLM (stream)                                        │
│      ├─ 处理 text-delta → 更新UI                             │
│      ├─ 处理 tool-call → 执行工具                             │
│      ├─ 处理 reasoning → 显示思考过程                         │
│      ↓                                                       │
│  5. 检查 finish_reason                                       │
│      ├─ "tool-calls" → 继续 Loop                             │
│      ├─ "stop"/"end-turn" → 退出 Loop                        │
│      └─ 其他 → 根据情况处理                                   │
│      ↓                                                       │
│  6. 返回最终响应                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 关键设计要点

1. **信任模型的判断**：让 LLM 自己决定何时完成任务（通过 `finish_reason`）

2. **工具执行后自动继续**：当模型调用工具时，系统自动处理工具执行并返回结果，模型持续"思考"直到它自己认为任务完成

3. **上下文管理**：当上下文溢出时，触发压缩机制（compaction），保留关键信息

4. **错误处理**：区分可重试错误和不可重试错误，自动重试或退出

5. **权限控制**：工具调用前检查权限，被拒绝时可以退出循环

---

## 核心源码文件

| 文件                    | 作用                   |
| ----------------------- | ---------------------- |
| `session/prompt.ts`     | 主循环逻辑、消息处理   |
| `session/processor.ts`  | 流式响应处理、工具执行 |
| `session/llm.ts`        | LLM 调用封装           |
| `session/message-v2.ts` | 消息结构定义           |
| `agent/agent.ts`        | Agent 配置和权限       |

---

## 总结

OpenCode 的连续性思考实现的核心思想是：

> **模型通过工具调用来"行动"，系统自动处理工具执行并返回结果，模型持续"思考"直到它自己认为任务完成。**

这种设计的优点：

- 简单可靠：依赖 LLM 自身的判断能力
- 灵活：支持任意数量的工具调用迭代
- 透明：用户可以看到每一步的思考过程

这种设计的缺点：

- 依赖模型能力：如果模型错误判断任务完成，可能会过早退出
- 无显式验证：不会主动验证任务是否真正完成
- 可能循环：在复杂任务中可能需要多次迭代
