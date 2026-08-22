export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  role: MessageRole;
  content: string;
}

export interface ResultPayload {
  scenario: string;
  calculator_output: Record<string, unknown>;
  explanation: string;
  assumptions: string[];
}

export interface ChatResponse {
  session_id: string;
  type: "clarifying_question" | "result" | "error";
  message: string;
  result: ResultPayload | null;
}
