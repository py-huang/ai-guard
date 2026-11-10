export type ConversationSource = {
  title: string;
};

export type ConversationCategory = "text" | "voice";

export type SafetyEventStatus = "pending" | "approved" | "revision" | "declined" | "cancelled" | "completed";

export type SafetyEvent = {
  id: string;
  type: "critical" | "pending" | "protected";
  createdAt: number;
  category: ConversationCategory | "image";
  maskedOriginal?: string;
  safeText?: string;
  fields?: string[];
  status?: SafetyEventStatus;
  read?: boolean;
  acknowledged?: boolean;
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
  category: ConversationCategory;
  topic?: string;
  messages: ConversationMessage[];
  safetyEvents?: SafetyEvent[];
};
