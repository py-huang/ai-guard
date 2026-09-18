import { ChildrenShell } from "@/components/children-shell";
import { AiTruthLesson, ImageLesson, PrivacyLesson, StrangerLesson } from "@/components/pages/ai-safety";

type SafetyDetailPageProps = {
  params: Promise<{ slug: string }>;
};

export default async function SafetyDetailPage({ params }: SafetyDetailPageProps) {
  const { slug } = await params;
  const lesson = slug === "ai-truth-lesson"
    ? <AiTruthLesson />
    : slug === "stranger-lesson"
      ? <StrangerLesson />
      : slug === "image-lesson"
        ? <ImageLesson />
        : <PrivacyLesson />;

  return (
    <ChildrenShell activeItem="AI 安全小幫手">
      {lesson}
    </ChildrenShell>
  );
}