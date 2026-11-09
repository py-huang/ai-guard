import { MobileHistoryDetail } from "@/components/pages/mobile-history";

type MobileHistoryDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function MobileHistoryDetailPage({ params }: MobileHistoryDetailPageProps) {
  const { id } = await params;
  return <MobileHistoryDetail conversationId={id} />;
}