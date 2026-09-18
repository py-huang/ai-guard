import { ChildrenShell } from "@/components/children-shell";
import { WritingWorkspace } from "@/components/pages/writing-workspace";

export default async function WritingThemePage({ params }: PageProps<"/theme/writing/[themeId]">) {
  const { themeId } = await params;

  return (
    <ChildrenShell activeItem="探索主題">
      <WritingWorkspace themeId={themeId} />
    </ChildrenShell>
  );
}