import { Download, FileArchive, ShieldCheck, Terminal, Check } from "lucide-react"

const contents = ["Cleaned Python Telegram bot", "Selar manual approval flow", "Supabase SQL migrations", "Deployment documentation"]

export default function DownloadPage() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-6 py-8 md:px-10 md:py-12">
        <header className="flex items-center justify-between border-b border-border pb-6">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground"><FileArchive className="size-5" aria-hidden="true" /></div>
            <span className="font-mono text-sm font-semibold tracking-tight">ANIME BOT / DELIVERY</span>
          </div>
          <span className="rounded-full border border-border px-3 py-1 font-mono text-xs text-muted-foreground">v1.0.0</span>
        </header>

        <section className="flex flex-1 flex-col justify-center py-16 md:py-24">
          <div className="max-w-3xl">
            <p className="mb-5 font-mono text-xs uppercase tracking-[0.22em] text-primary">Verified project archive</p>
            <h1 className="max-w-3xl text-balance text-4xl font-semibold tracking-[-0.04em] md:text-6xl md:leading-[1.05]">Your clean project is ready to download.</h1>
            <p className="mt-6 max-w-2xl text-pretty text-base leading-7 text-muted-foreground md:text-lg">This is the correct archive. It contains the working anime bot project without nested ZIP files, temporary caches, or Python bytecode.</p>
          </div>

          <div className="mt-12 grid gap-5 md:grid-cols-[1.25fr_0.75fr]">
            <div className="rounded-2xl border border-border bg-card p-6 md:p-8">
              <div className="flex items-start justify-between gap-6">
                <div><p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Download file</p><h2 className="mt-3 text-xl font-semibold tracking-tight">anime-bot-clean.zip</h2><p className="mt-2 font-mono text-sm text-muted-foreground">Clean archive · ready for deployment</p></div>
                <div className="hidden rounded-xl bg-secondary p-3 text-primary md:block"><FileArchive className="size-6" aria-hidden="true" /></div>
              </div>
              <a href="/downloads/anime-bot-clean.zip" download className="mt-8 flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 py-4 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><Download className="size-4" aria-hidden="true" />Download the ZIP</a>
              <p className="mt-4 text-center text-xs text-muted-foreground">The download starts directly from this page.</p>
            </div>
            <div className="rounded-2xl border border-border bg-card p-6 md:p-8"><p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Included</p><ul className="mt-5 space-y-4">{contents.map((item) => <li key={item} className="flex gap-3 text-sm leading-5"><Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" /><span>{item}</span></li>)}</ul></div>
          </div>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <div className="flex items-start gap-4 rounded-2xl border border-border bg-secondary/40 p-5"><ShieldCheck className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" /><div><h3 className="text-sm font-semibold">Cleaned before delivery</h3><p className="mt-1 text-sm leading-6 text-muted-foreground">Nested ZIP files, caches, and bytecode are excluded from this archive.</p></div></div>
            <div className="flex items-start gap-4 rounded-2xl border border-border bg-secondary/40 p-5"><Terminal className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" /><div><h3 className="text-sm font-semibold">Start here</h3><p className="mt-1 text-sm leading-6 text-muted-foreground">Extract the ZIP, open the anime-bot-main folder, then follow its deployment guide.</p></div></div>
          </div>
        </section>
        <footer className="border-t border-border pt-5 font-mono text-xs text-muted-foreground">anime-bot-clean.zip · direct project delivery</footer>
      </div>
    </main>
  )
}
