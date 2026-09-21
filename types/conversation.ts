export type ConversationMessage = {
  role: "user" | "assistant" | "system-note";
  content: string;
  protected?: boolean;
  blocked?: boolean;
  hasImage?: boolean;
};

export type Conversation = {
  id: string;
  title: string;
  updatedAt: number;
  topic?: string;
  messages: ConversationMessage[];
};
