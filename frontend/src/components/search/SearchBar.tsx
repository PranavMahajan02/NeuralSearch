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
    if (event.key === "ArrowDown" && items.length) {
      event.preventDefault();
      setOpen(true);
      setActive((i) => (i + 1) % items.length);
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
    <form role="search" onSubmit={onFormSubmit} className="relative">
      <label htmlFor="search-input" className="sr-only">
        Search your files
      </label>
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute left-3 top-3 h-5 w-5 text-slate-500"
      />
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
        placeholder='Search documents, images, audio and video…  (press "/")'
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
        className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-24 text-base shadow-sm placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-900"
      />
      <button
        type="submit"
        className="absolute right-1.5 top-1.5 rounded-lg bg-blue-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-800"
      >
        Search
      </button>
      {items.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          aria-label="Matching file names"
          className="absolute z-30 mt-1 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"
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
              className={`flex cursor-pointer items-center gap-2 px-3 py-2 text-sm ${
                index === active ? "bg-blue-50 dark:bg-blue-950" : "hover:bg-slate-50 dark:hover:bg-slate-800"
              }`}
            >
              <TypeIcon type={item.type} className="h-4 w-4 shrink-0 text-slate-500" />
              <span className="truncate">{item.file}</span>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
