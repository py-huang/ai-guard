import { ChildrenShell } from "@/components/children-shell";
import { Chat } from "@/components/pages/chat";

type ChatDetailPageProps = {
  params: Promise<{ slug: string }>;
};

export default async function ChatDetailPage({ params }: ChatDetailPageProps) {
  const { slug } = await params;

  return (
    <ChildrenShell>
      <Chat conversationId={slug} />
    </ChildrenShell>
  );
}
