import { ChildrenShell } from "@/components/children-shell";
import { AiSafety } from "@/components/pages/ai-safety";

export default function SafetyDetailPage() {
  return (
    <ChildrenShell activeItem="AI 安全小幫手">
      <AiSafety />
    </ChildrenShell>
  );
}