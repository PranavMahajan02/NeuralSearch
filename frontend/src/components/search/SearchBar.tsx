import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";

import * as api from "../../api/endpoints";
import { keys } from "../../api/queries";
import { useAuth } from "../../auth/AuthContext";
import { useDebounced } from "../../hooks/useDebounced";
import { TypeIcon } from "../common/Badges";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (query: string) => void;
}

function isEditable(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return (
    !!el &&
    (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable)
  );
}

/** Search box with file-name autocomplete (ARIA combobox). "/" focuses it from anywhere. */
export function SearchBar({ value, onChange, onSubmit }: SearchBarProps) {
  const { userId } = useAuth();
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const prefix = useDebounced(value.trim(), 150);

  const suggestions = useQuery({
    queryKey: keys.suggestions(userId, prefix),
    queryFn: ({ signal }) => api.getSuggestions(prefix, signal),
    enabled: open && prefix.length >= 2,
    staleTime: 60_000,
  });

  const items = open && prefix.length >= 2 ? (suggestions.data?.suggestions ?? []) : [];

  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "/" && !isEditable(event.target) && !event.ctrlKey && !event.metaKey) {
        event.preventDefault();
        input.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const submit = (query: string) => {
    setOpen(false);
    setActive(-1);
    if (query.trim()) onSubmit(query.trim());
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    const available = prefix.length >= 2 ? (suggestions.data?.suggestions ?? []) : [];

    if (event.key === "ArrowDown" && available.length) {
      event.preventDefault();
      if (!open) {
        // Reopen a list closed with Esc (ARIA combobox pattern).
        setOpen(true);
        setActive(0);
      } else {
        setActive((i) => (i + 1) % available.length);
      }
    } else if (event.key === "ArrowUp" && items.length) {
      event.preventDefault();
      setActive((i) => (i <= 0 ? items.length - 1 : i - 1));
    } else if (event.key === "Enter" && active >= 0 && items[active]) {
      event.preventDefault();
      onChange(items[active].file);
      submit(items[active].file);
    } else if (event.key === "Escape") {
      if (open && items.length) {
        event.preventDefault();
        setOpen(false);
        setActive(-1);
      } else {
        input.current?.blur();
      }
    }
  };

  const onFormSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit(value);
  };

  return (
    <form role="search" onSubmit={onFormSubmit} className="relative z-10 mx-auto max-w-3xl">
      <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-lg shadow-slate-100/50 transition-colors duration-200 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:shadow-slate-950/40 dark:hover:border-slate-700">
        <div className="flex w-full flex-1 items-center gap-2.5 px-3">
          <Search aria-hidden="true" className="h-5 w-5 shrink-0 text-slate-500" />
          <label htmlFor="search-input" className="sr-only">
            Search your files
          </label>
          <input
            ref={input}
            id="search-input"
            type="search"
            role="combobox"
            aria-expanded={items.length > 0}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={active >= 0 && items[active] ? `${listId}-${active}` : undefined}
            autoComplete="off"
            placeholder='Search papers, code, screenshots, audio transcripts…  (press "/")'
            value={value}
            maxLength={500}
            onChange={(event) => {
              onChange(event.target.value);
              setOpen(true);
              setActive(-1);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 120)}
            onKeyDown={onKeyDown}
            className="w-full bg-transparent py-2.5 text-sm font-medium text-slate-800 placeholder-slate-500 focus:outline-none dark:text-slate-100 [&::-webkit-search-cancel-button]:hidden"
          />
          {value && (
            <button
              type="button"
              onClick={() => {
                onChange("");
                input.current?.focus();
              }}
              className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:text-slate-800 dark:bg-slate-800 dark:text-slate-300 dark:hover:text-white"
            >
              Clear
            </button>
          )}
        </div>
        <button
          type="submit"
          className="shrink-0 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-xs transition-all hover:bg-blue-700 active:scale-97"
        >
          Search
        </button>
      </div>
      {items.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          aria-label="Matching file names"
          className="absolute z-30 mt-1.5 w-full overflow-hidden rounded-2xl border border-slate-200/90 bg-white p-1.5 shadow-xl shadow-slate-200/40 dark:border-slate-800 dark:bg-slate-900 dark:shadow-slate-950/60"
        >
          {items.map((item, index) => (
            <li
              key={`${item.platform}-${item.file}`}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              onMouseDown={(event) => {
                event.preventDefault();
                onChange(item.file);
                submit(item.file);
              }}
              className={`flex cursor-pointer items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold ${
                index === active
                  ? "bg-blue-600 text-white"
                  : "text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              <TypeIcon type={item.type} className="h-4 w-4 shrink-0" />
              <span className="truncate">{item.file}</span>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
