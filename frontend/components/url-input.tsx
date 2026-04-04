"use client";

import { useCallback, useState, type FormEvent, type KeyboardEvent } from "react";

export function validateHttpUrl(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) return false;
  try {
    const u = new URL(trimmed);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

type UrlInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  error: string | null;
  disabled?: boolean;
};

export function UrlInput({
  value,
  onChange,
  onSubmit,
  loading,
  error,
  disabled,
}: UrlInputProps) {
  const [focused, setFocused] = useState(false);

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      onSubmit();
    },
    [onSubmit],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        onSubmit();
      }
    },
    [onSubmit],
  );

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div
        className={`relative flex flex-col gap-3 rounded-2xl border bg-[#111827]/80 p-2 shadow-[0_0_0_1px_rgb(30_41_59_0.8)] backdrop-blur-md transition-all duration-300 sm:flex-row sm:items-stretch sm:p-2 ${
          focused
            ? "border-cyan-400/50 shadow-[0_0_40px_-8px_rgb(34_211_238_0.35),0_0_0_1px_rgb(34_211_238_0.25)]"
            : "border-slate-700/80 hover:border-slate-600"
        }`}
      >
        <div className="relative flex min-h-[3.5rem] flex-1 items-center gap-3 pl-3 pr-2 sm:pl-4">
          <span
            className="pointer-events-none flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/20 to-violet-600/20 text-cyan-300 ring-1 ring-cyan-400/20"
            aria-hidden
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Z" />
              <path d="M12 4v4M12 16v4M4 12h4M16 12h4" />
              <circle cx="12" cy="12" r="2" fill="currentColor" stroke="none" />
            </svg>
          </span>
          <input
            type="url"
            inputMode="url"
            autoComplete="url"
            placeholder="Paste a website URL..."
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={handleKeyDown}
            disabled={disabled || loading}
            className="h-12 w-full min-w-0 bg-transparent text-base text-slate-100 placeholder:text-slate-500 focus:outline-none disabled:opacity-50"
          />
        </div>
        <button
          type="submit"
          disabled={disabled || loading}
          className="group relative flex h-12 shrink-0 items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-violet-600 px-8 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 transition hover:brightness-110 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 sm:h-auto sm:self-stretch sm:rounded-xl sm:px-10"
        >
          <span className="relative z-10">
            {loading ? (
              <span className="flex items-center gap-2">
                <span
                  className="inline-block h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-neuro-spin"
                  aria-hidden
                />
                Analyzing…
              </span>
            ) : (
              "Analyze"
            )}
          </span>
          <span
            className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 opacity-0 transition group-hover:opacity-100"
            aria-hidden
          />
        </button>
      </div>
      {error ? (
        <p
          className="mt-3 animate-neuro-fade-in text-sm font-medium text-red-400"
          role="alert"
        >
          {error}
        </p>
      ) : null}
    </form>
  );
}
