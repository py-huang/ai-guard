export type ConversationSource = {
  title: string;
};

export type ConversationMessage = {
  role: "user" | "assistant" | "system-note";
  content: string;
  protected?: boolean;
  blocked?: boolean;
  hasImage?: boolean;
  imagePreview?: string;
  sources?: ConversationSource[];
};

export type Conversation = {
  id: string;
  title: string;
  updatedAt: number;
  topic?: string;
  messages: ConversationMessage[];
};
