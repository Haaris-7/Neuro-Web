import Link from "next/link";

export default async function ResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="min-h-screen bg-[#0a0e1a] px-6 py-16 text-slate-100">
      <div className="mx-auto max-w-lg text-center">
        <h1 className="mb-4 text-2xl font-bold text-slate-50">Results</h1>
        <p className="mb-2 font-mono text-sm text-slate-500">Job {id}</p>
        <p className="mb-8 text-slate-400">
          Full results dashboard will appear here in a future release.
        </p>
        <Link
          href="/"
          className="inline-flex rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 px-6 py-2.5 text-sm font-semibold text-white hover:brightness-110"
        >
          New analysis
        </Link>
      </div>
    </div>
  );
}
