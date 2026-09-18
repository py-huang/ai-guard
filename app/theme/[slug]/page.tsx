import { ChildrenShell } from "@/components/children-shell";
import { DiscoverTheme } from "@/components/pages/discover-theme";

export default function ThemeDetailPage() {
  return (
    <ChildrenShell activeItem="探索主題">
      <DiscoverTheme />
    </ChildrenShell>
  );
}