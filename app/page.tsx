import { ChildrenShell } from "@/components/children-shell";
import { DiscoverHome } from "@/components/pages/discover-home";

export default function Home() {
  return (
    <ChildrenShell activeItem="探索首頁">
      <DiscoverHome />
    </ChildrenShell>
  );
}
