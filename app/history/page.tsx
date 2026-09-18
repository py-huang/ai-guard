import { ChildrenShell } from "@/components/children-shell";
import { ChatHistory } from "@/components/pages/chat-history";

export default function HistoryPage() {
  return (
    <ChildrenShell activeItem="對話紀錄">
      <ChatHistory />
    </ChildrenShell>
  );
}