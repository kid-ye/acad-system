import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ChartBar,
  ChatCircleText,
  DownloadSimple,
  House,
  MagnifyingGlass,
} from "@phosphor-icons/react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from "./ui/command";
import { getCourses, type Course } from "../api";

const ROUTES = [
  { label: "Home", to: "/home", icon: House, shortcut: "" },
  { label: "Ask the archive", to: "/ask", icon: ChatCircleText, shortcut: "" },
  { label: "Course statistics", to: "/stats", icon: ChartBar, shortcut: "" },
  { label: "Download papers", to: "/download", icon: DownloadSimple, shortcut: "" },
];

export default function CommandK({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [query, setQuery] = useState("");
  const [courses, setCourses] = useState<Course[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) {
      setQuery("");
      setCourses([]);
    }
  }, [open]);

  useEffect(() => {
    if (query.trim().length < 2) return setCourses([]);
    const t = setTimeout(() => {
      getCourses(query.trim())
        .then(setCourses)
        .catch(() => setCourses([]));
    }, 200);
    return () => clearTimeout(t);
  }, [query]);

  const go = useCallback(
    (path: string) => {
      onOpenChange(false);
      navigate(path);
    },
    [navigate],
  );

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Command palette"
      description="Navigate, search courses, or ask a question."
      showCloseButton={false}
    >
      <CommandInput
        placeholder="Where to? Search courses, jump to a page…"
        value={query}
        onValueChange={setQuery}
      />
      <CommandList className="h-[300px]">
        <CommandEmpty>
          {query.trim().length < 2
            ? "Type to search courses…"
            : "No results."}
        </CommandEmpty>

        <CommandGroup heading="Pages">
          {ROUTES.map((r) => (
            <CommandItem key={r.to} onSelect={() => go(r.to)}>
              <r.icon size={16} weight="regular" />
              {r.label}
              {r.shortcut && <CommandShortcut>{r.shortcut}</CommandShortcut>}
            </CommandItem>
          ))}
          {query.trim() && (
            <CommandItem
              onSelect={() => go(`/ask`)}
              value={`ask: ${query}`}
            >
              <ChatCircleText size={16} weight="regular" />
              Ask "{query}"
            </CommandItem>
          )}
        </CommandGroup>

        {courses.length > 0 && (
          <CommandGroup heading="Courses">
            {courses.slice(0, 8).map((c) => (
              <CommandItem
                key={c.course_code}
                value={`${c.course_code} ${c.course_name}`}
                onSelect={() =>
                  go(`/stats?course=${encodeURIComponent(c.course_code)}`)
                }
              >
                <MagnifyingGlass size={16} weight="regular" />
                <span className="font-mono text-xs">{c.course_code}</span>
                <span className="truncate text-ink-2">{c.course_name}</span>
                <CommandShortcut>
                  {c.question_count} q
                </CommandShortcut>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
      </CommandList>
    </CommandDialog>
  );
}
