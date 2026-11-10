export type ConversationSource = {
  title: string;
};

export type ConversationCategory = "text" | "voice";

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
  category: ConversationCategory;
  topic?: string;
  messages: ConversationMessage[];
};
