"use client";

import DemoLiveToggle from "./DemoLiveToggle";
import StatusIndicator from "./StatusIndicator";

export default function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-[#1E293B] bg-[#0F172A] px-8">
      <StatusIndicator />
      <div className="flex items-center gap-4">
        <DemoLiveToggle />
      </div>
    </header>
  );
}
