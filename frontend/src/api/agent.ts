export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export type AgentEvent =
  | { type: 'text'; content: string }
  | { type: 'tool_call'; id: string; name: string; arguments: Record<string, unknown> }
  | { type: 'tool_result'; name: string; result: string }
  | { type: 'error'; message: string }

/**
 * 向后端 /api/v1/agent/chat 发起 POST 请求并以 SSE 流式消费。
 * 后端返回的事件负载已包含 type 字段，直接透传给回调。
 */
export async function streamAgentChat(
  messages: ChatMessage[],
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch('/api/v1/agent/chat', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
    signal,
  })

  if (!resp.ok || !resp.body) {
    let message = `请求失败（${resp.status}）`
    try {
      const data = await resp.json()
      if (data.detail) message = data.detail
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const parse = (chunk: string) => {
    buffer += chunk
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const raw = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      let dataLines: string[] = []
      for (const line of raw.split('\n')) {
        if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
      }
      if (dataLines.length === 0) continue
      try {
        onEvent(JSON.parse(dataLines.join('\n')) as AgentEvent)
      } catch {
        /* ignore malformed frame */
      }
    }
  }

  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    parse(decoder.decode(value, { stream: true }))
  }
  parse(decoder.decode())
}