export function MobilePlaceholder({ title, message }: { title: string; message: string }) {
  return (
    <section className="flex h-full flex-col bg-[#fffcf7]">
      <header className="flex h-16 shrink-0 items-center bg-white px-4">
        <h1 className="text-[18px] font-bold leading-7">{title}</h1>
      </header>
      <div className="flex flex-1 items-start p-4">
        <p className="w-full rounded-[20px] border border-[#dde3df] bg-white p-4 text-[13px] leading-5 text-[#506058]">{message}</p>
      </div>
    </section>
  );
}