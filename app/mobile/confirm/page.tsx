import { MobileNotifications } from "@/components/pages/mobile-notifications";
import { Suspense } from "react";

export default function MobileConfirmPage() {
  return <Suspense><MobileNotifications confirmationsOnly /></Suspense>;
}