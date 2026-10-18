import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Ext } from "./ExternalLink";
import { ReviewQueue } from "./ReviewQueue";
import { useTheme } from "./useTheme";
import {
  ArrowUpRight,
  ArrowRight,
  Bookmark,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Download,
  Heart,
  LayoutList,
  CalendarDays,
  RefreshCw,
  Search,
  SlidersHorizontal,
  X,
  Eye,
  Plus,
  CheckCheck,
  Link,
  Radio,
  AlertCircle,
  Sun,
  Moon,
} from "lucide-react";
import type {
  ArtEvent,
  Catalog,
  Feed,
  Filters,
  Institution,
  Personal,
  ReviewData,
} from "./types";
import {
  CONFIG,
  EVENT_TYPES,
  PLATFORM,
  STATUS,
  STATES,
  TAGS,
  CATEGORIES,
} from "./config";
import {
  DEFAULT_FILTERS,
  dayLabel,
  downloadICS,
  filterEvents,
  filterInstitutions,
  filtersFromURL,
  isOngoing,
  loadPersonal,
  moscowToday,
  normalize,
  plusDays,
  stamp,
} from "./lib";

const NAV = [
  { id: "agenda", label: "Афиша" },
  { id: "calendar", label: "Календарь" },
  { id: "spaces", label: "Пространства" },
  { id: "sources", label: "Источники" },
  { id: "review", label: "На проверке" },
];
const PERIODS = [
  { id: "upcoming", label: "Предстоящие" },
  { id: "today", label: "Сегодня" },
  { id: "tomorrow", label: "Завтра" },
  { id: "week", label: "На этой неделе" },
  { id: "ongoing", label: "Сейчас идут" },
  { id: "archive", label: "Архив" },
];
const pad = (n: number) => String(n).padStart(2, "0");
function Toggle({
  checked,
  onChange,
  children,
}: {
  checked: boolean;
  onChange: () => void;
  children: ReactNode;
}) {
  return (
    <label className="check-label">
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className="check-box">{checked && <Check size={11} />}</span>
      <span>{children}</span>
    </label>
  );
}
function Dialog({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const prior = document.activeElement as HTMLElement;
    panel.current?.focus();
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeRef.current();
      if (e.key === "Tab") {
        const els = panel.current?.querySelectorAll<HTMLElement>(
          'a[href],button,input,select,textarea,[tabindex="0"]',
        );
        if (!els?.length) return;
        const first = els[0],
          last = els[els.length - 1];
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === panel.current)
        ) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = old;
      document.removeEventListener("keydown", key);
      prior?.focus();
    };
  }, []);
  return (
    <div
      className="dialog-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={`dialog ${wide ? "dialog-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        tabIndex={-1}
        ref={panel}
      >
        <div className="dialog-top">
          <span className="eyebrow">АРТ-КАЛЕНДАРЬ / ДОСЬЕ</span>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Закрыть"
          >
            <X size={22} />
          </button>
        </div>
        <h2 id="dialog-title">{title}</h2>
        {children}
      </div>
    </div>
  );
}

function MiniCalendar({
  month,
  setMonth,
  selected,
  onSelect,
  events,
  large = false,
  week = false,
}: {
  month: string;
  setMonth: (m: string) => void;
  selected: string;
  onSelect: (d: string) => void;
  events: ArtEvent[];
  large?: boolean;
  week?: boolean;
}) {
  const first = month.slice(0, 7) + "-01";
  const firstDay = (new Date(first + "T12:00:00Z").getUTCDay() + 6) % 7;
  const days = new Date(
    Number(month.slice(0, 4)),
    Number(month.slice(5, 7)),
    0,
  ).getDate();
  const shift = (n: number) => {
    const d = new Date(first + "T12:00:00Z");
    d.setUTCMonth(d.getUTCMonth() + n);
    setMonth(d.toISOString().slice(0, 10));
  };
  let cells = Array.from(
    { length: Math.ceil((firstDay + days) / 7) * 7 },
    (_, i) => plusDays(first, i - firstDay),
  );
  if (week) {
    const day = selected || moscowToday();
    const offset = (new Date(day + "T12:00:00Z").getUTCDay() + 6) % 7;
    cells = Array.from({ length: 7 }, (_, i) => plusDays(day, i - offset));
  }
  return (
    <div className={`${large ? "full-calendar" : "mini-calendar"}`}>
      <div className="calendar-heading">
        <span>
          {week
            ? `${dayLabel(cells[0], { day: "numeric", month: "short" })} — ${dayLabel(cells[6])}`
            : dayLabel(first, { month: "long", year: "numeric" })}
        </span>
        <div>
          <button
            className="icon-button"
            onClick={() =>
              week
                ? onSelect(plusDays(selected || moscowToday(), -7))
                : shift(-1)
            }
            aria-label={week ? "Предыдущая неделя" : "Предыдущий месяц"}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            className="icon-button"
            onClick={() =>
              week ? onSelect(plusDays(selected || moscowToday(), 7)) : shift(1)
            }
            aria-label={week ? "Следующая неделя" : "Следующий месяц"}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
      <div className="calendar-weekdays">
        {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>
      <div className="calendar-days">
        {cells.map((day) => {
          const count = events.filter(
            (e) => e.start_date <= day && (e.end_date || e.start_date) >= day,
          ).length;
          return (
            <button
              key={day}
              className={`${day.slice(0, 7) !== month.slice(0, 7) && !week ? "outside" : ""} ${day === moscowToday() ? "is-today" : ""} ${selected === day ? "selected" : ""}`}
              onClick={() => onSelect(day)}
              aria-label={`${dayLabel(day)}, событий: ${count}`}
              aria-pressed={selected === day}
            >
              <span>{Number(day.slice(-2))}</span>
              {large && count > 0 ? (
                <small>
                  {count} {count === 1 ? "событие" : "события"}
                </small>
              ) : count > 0 ? (
                <i />
              ) : null}
            </button>
          );
        })}
      </div>
      {!large && (
        <div className="calendar-key">
          <span className="tiny-dot" /> Сегодня, по Москве
        </div>
      )}
    </div>
  );
}

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [feed, setFeed] = useState<Feed | null>(null);
  const [review, setReview] = useState<ReviewData | null>(null);
  const [reviewError, setReviewError] = useState("");
  const [reviewReason, setReviewReason] = useState("");
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState("");
  const [filters, setFilters] = useState<Filters>(filtersFromURL);
  const [view, setView] = useState(() => {
    const v = new URLSearchParams(location.search).get("view");
    return NAV.some((n) => n.id === v) ? v! : "agenda";
  });
  const [personal, setPersonal] = useState<Personal>(loadPersonal);
  const [mobileFilters, setMobileFilters] = useState(false);
  const [method, setMethod] = useState(false);
  const [eventId, setEventId] = useState(
    new URLSearchParams(location.search).get("event") || "",
  );
  const [spaceId, setSpaceId] = useState(() => {
    const p = new URLSearchParams(location.search);
    return p.has("event") ? "" : p.get("space") || "";
  });
  const [month, setMonth] = useState(
    (filters.from || moscowToday()).slice(0, 7) + "-01",
  );
  const [calendarDay, setCalendarDay] = useState(() => {
    return filters.from === filters.to ? filters.from : "";
  });
  const [calendarMode, setCalendarMode] = useState("month");
  const [sourceStatus, setSourceStatus] = useState("");
  const [directoryState, setDirectoryState] = useState("");
  const [visibleSpaces, setVisibleSpaces] = useState(18);
  const today = moscowToday();
  const sourceMap = useMemo(
    () => new Map(feed?.sources.map((s) => [s.source_id, s])),
    [feed],
  );
  const patch = (f: Partial<Filters>) => {
    setFilters((old) => ({ ...old, ...f }));
    setVisibleSpaces(18);
  };
  const reset = () => {
    setFilters({ ...DEFAULT_FILTERS });
    setCalendarDay("");
    setSourceStatus("");
    setReviewReason("");
    setDirectoryState("");
    setVisibleSpaces(18);
  };
  const notify = (message: string) => setToast(message);
  const fetchData = async (initial = false) => {
    setRefreshing(true);
    try {
      const nonce = Date.now();
      const [cr, fr, rr] = await Promise.all([
        fetch(`${import.meta.env.BASE_URL}data/catalog.json?t=${nonce}`, {
          cache: "no-store",
        }),
        fetch(`${import.meta.env.BASE_URL}data/events.json?t=${nonce}`, {
          cache: "no-store",
        }),
        fetch(`${import.meta.env.BASE_URL}data/review.json?t=${nonce}`, {
          cache: "no-store",
        })
          .then(async (response) => {
            if (!response.ok) throw new Error("queue unavailable");
            const data = await response.json();
            if (!Array.isArray(data.items)) throw new Error("invalid queue");
            return data as ReviewData;
          })
          .catch(() => null),
      ]);
      if (!cr.ok || !fr.ok)
        throw new Error(
          "Данные ещё не опубликованы. Импортируйте каталог и запустите сборщик.",
        );
      const c = await cr.json(),
        f = await fr.json();
      if (
        !Array.isArray(c.institutions) ||
        !Array.isArray(f.events) ||
        !f.metadata
      )
        throw new Error("Формат опубликованных данных не распознан.");
      setCatalog(c);
      setFeed(f);
      setReview(rr);
      setReviewError(
        rr
          ? ""
          : "Не удалось загрузить очередь проверки. Афиша и каталог доступны.",
      );
      setError("");
      if (!initial)
        notify(
          "Опубликованные данные загружены. Новая проверка источников не запускалась.",
        );
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Не удалось загрузить данные. Попробуйте ещё раз.",
      );
    } finally {
      setRefreshing(false);
    }
  };
  useEffect(() => {
    void fetchData(true);
    try {
      localStorage.setItem("art-monitor:last-visit", new Date().toISOString());
    } catch {}
    const key = (e: KeyboardEvent) => {
      if (
        e.key === "/" &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement) &&
        !(e.target instanceof HTMLSelectElement)
      ) {
        e.preventDefault();
        document
          .querySelector<HTMLInputElement>(".search-field input")
          ?.focus();
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem("art-monitor:personal", JSON.stringify(personal));
    } catch {
      /* Private browsing: session remains functional. */
    }
  }, [personal]);
  useEffect(() => {
    if (eventId && feed?.events.some((e) => e.event_id === eventId))
      setPersonal((p) =>
        p.read.includes(eventId) ? p : { ...p, read: [...p.read, eventId] },
      );
  }, [eventId, feed]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 5500);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    const p = new URLSearchParams();
    if (view !== "agenda") p.set("view", view);
    const map: Record<string, string> = {
      q: filters.q,
      geography: filters.geography === "moscow" ? "" : filters.geography,
      period: filters.period === "upcoming" ? "" : filters.period,
      type: filters.types.join(","),
      institution: filters.institution,
      district: filters.district,
      category: filters.category,
      scene: filters.scene,
      new: filters.onlyNew ? "1" : "",
      saved: filters.onlySaved ? "1" : "",
      favorites: filters.onlyFavorites ? "1" : "",
      sort: filters.sort === "date" ? "" : filters.sort,
      from: filters.from,
      to: filters.to,
    };
    Object.entries(map).forEach(([k, v]) => {
      if (v) p.set(k, v);
    });
    if (eventId) p.set("event", eventId);
    if (spaceId) p.set("space", spaceId);
    history.replaceState(
      null,
      "",
      location.pathname + (p.size ? "?" + p.toString() : ""),
    );
  }, [view, filters, eventId, spaceId]);
  useEffect(() => {
    const pop = () => {
      const p = new URLSearchParams(location.search);
      setFilters(filtersFromURL());
      setView(p.get("view") || "agenda");
      setEventId(p.get("event") || "");
      setSpaceId(p.get("space") || "");
    };
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  const togglePersonal = (key: "favorites" | "saved" | "read", id: string) =>
    setPersonal((p) => ({
      ...p,
      [key]: p[key].includes(id)
        ? p[key].filter((x) => x !== id)
        : [...p[key], id],
    }));
  const openEvent = (e: ArtEvent) => {
    setEventId(e.event_id);
    setPersonal((p) => ({ ...p, read: [...new Set([...p.read, e.event_id])] }));
  };
  const events = useMemo(
    () =>
      filterEvents(
        feed?.events || [],
        catalog?.institutions || [],
        filters,
        personal,
        today,
      ),
    [feed, catalog, filters, personal, today],
  );
  const spaces = useMemo(
    () =>
      filterInstitutions(catalog?.institutions || [], filters, personal)
        .filter((i) => !directoryState || i.monitor_state === directoryState)
        .sort(
          (a, b) =>
            Number(b.independent) - Number(a.independent) ||
            a.name.localeCompare(b.name, "ru"),
        ),
    [catalog, filters, personal, directoryState],
  );
  const selectedEvent = feed?.events.find((e) => e.event_id === eventId);
  const selectedSpace = catalog?.institutions.find(
    (i) => i.institution_id === spaceId,
  );
  const eventInstitution = catalog?.institutions.find(
    (i) => i.institution_id === selectedEvent?.institution_id,
  );
  const eventAddress =
    selectedEvent?.address ||
    (eventInstitution?.locations.length === 1
      ? eventInstitution.locations[0].address
      : undefined);
  const eventView = view === "agenda" || view === "calendar";
  const activeFilters: { id: string; label: string; remove: () => void }[] = [];
  const addFilter = (id: string, label: string, remove: () => void) =>
    activeFilters.push({ id, label, remove });
  if (filters.q) addFilter("q", `Поиск: ${filters.q}`, () => patch({ q: "" }));
  if (filters.scene)
    addFilter(
      "scene",
      filters.scene === "independent"
        ? "Независимая сцена"
        : "Институции и музеи",
      () => patch({ scene: "" }),
    );
  if (filters.category)
    addFilter(
      "category",
      `Тип пространства: ${CATEGORIES[filters.category] || filters.category}`,
      () => patch({ category: "" }),
    );
  if (filters.institution)
    addFilter(
      "institution",
      catalog?.institutions.find(
        (i) => i.institution_id === filters.institution,
      )?.name || filters.institution,
      () => patch({ institution: "" }),
    );
  if (filters.district)
    addFilter("district", `Район: ${filters.district}`, () =>
      patch({ district: "" }),
    );
  if (filters.onlyFavorites)
    addFilter("favorites", "Мои пространства", () =>
      patch({ onlyFavorites: false }),
    );
  if (eventView) {
    if (filters.geography !== "moscow")
      addFilter(
        "geography",
        filters.geography === "all" ? "Москва и Подмосковье" : "Подмосковье",
        () => patch({ geography: "moscow" }),
      );
    filters.types.forEach((type) =>
      addFilter(`type:${type}`, EVENT_TYPES[type] || type, () =>
        patch({ types: filters.types.filter((t) => t !== type) }),
      ),
    );
    if (filters.onlyNew)
      addFilter("new", "Новые с прошлого визита", () =>
        patch({ onlyNew: false }),
      );
    if (filters.onlySaved)
      addFilter("saved", "Сохранённые события", () =>
        patch({ onlySaved: false }),
      );
    if (
      filters.period !== "upcoming" &&
      !(filters.period === "all" && (filters.from || filters.to))
    )
      addFilter(
        "period",
        `Период: ${PERIODS.find((p) => p.id === filters.period)?.label || "Все даты"}`,
        () => {
          patch({ period: "upcoming" });
          setCalendarDay("");
        },
      );
    if (filters.from)
      addFilter("from", `С ${dayLabel(filters.from)}`, () => {
        patch({ from: "", period: filters.to ? "all" : "upcoming" });
        setCalendarDay("");
      });
    if (filters.to)
      addFilter("to", `По ${dayLabel(filters.to)}`, () => {
        patch({ to: "", period: filters.from ? "all" : "upcoming" });
        setCalendarDay("");
      });
    if (filters.sort !== "date")
      addFilter("sort", "По дате обнаружения", () => patch({ sort: "date" }));
  }
  if (view === "spaces" && directoryState)
    addFilter(
      "directoryState",
      `Статус: ${STATES[directoryState] || directoryState}`,
      () => {
        setDirectoryState("");
        setVisibleSpaces(18);
      },
    );
  if (view === "sources" && sourceStatus)
    addFilter(
      "sourceStatus",
      `Статус: ${STATUS[sourceStatus] || sourceStatus}`,
      () => setSourceStatus(""),
    );
  if (view === "review" && reviewReason)
    addFilter("reviewReason", `Причина: ${reviewReason}`, () =>
      setReviewReason(""),
    );
  const activeCount = activeFilters.length;
  const monitorCount =
    catalog?.institutions.filter((i) => i.monitor_state === "monitor").length ||
    0;
  const checkedCount =
    feed?.sources.filter(
      (s) => s.status === "working" || s.status === "partial",
    ).length || 0;
  const navigate = (id: string) => {
    setView(id);
    setMobileFilters(false);
    setEventId("");
    setSpaceId("");
  };
  const setFavoriteView = () => {
    navigate("spaces");
    patch({ onlyFavorites: !filters.onlyFavorites, onlySaved: false });
  };
  const datesInCalendar = filterEvents(
    feed?.events || [],
    catalog?.institutions || [],
    { ...filters, period: "all", from: "", to: "" },
    personal,
    today,
  );

  const hiddenRegionalCount =
    eventView && filters.geography === "moscow"
      ? filterEvents(
          feed?.events || [],
          catalog?.institutions || [],
          { ...filters, geography: "moscow_region" },
          personal,
          today,
        ).length
      : 0;

  const filterSummary = (
    <>
      {(feed?.metadata.run_status === "blocked" || feed?.metadata.partial) && (
        <div className="coverage-note">
          <Radio size={15} />
          <span>
            {feed.metadata.run_status === "blocked"
              ? "Афиша ещё не подтверждена."
              : "Охват неполный."}{" "}
            {checkedCount} из {catalog?.sources.length} источников доступны для
            автоматической проверки.
          </span>
          {view !== "sources" && (
            <button onClick={() => navigate("sources")}>
              Статус источников <ArrowUpRight size={13} />
            </button>
          )}
        </div>
      )}
      {activeCount > 0 && (
        <div
          className="active-filters"
          role="region"
          aria-label="Выбранные фильтры"
        >
          <ul>
            {activeFilters.map((item) => (
              <li key={item.id}>
                <button
                  className="filter-tag"
                  onClick={item.remove}
                  aria-label={`Убрать фильтр: ${item.label}`}
                >
                  <span>{item.label}</span>
                  <X size={16} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
          <button className="clear-filters" onClick={reset}>
            Сбросить фильтры
          </button>
        </div>
      )}
      {eventView && (
        <div className="geography-note">
          <span>
            География:{" "}
            {filters.geography === "moscow"
              ? "только Москва"
              : filters.geography === "all"
                ? "Москва и Подмосковье"
                : "только Подмосковье"}
            .
            {hiddenRegionalCount > 0 &&
              ` По остальным фильтрам в Подмосковье найдено ещё: ${hiddenRegionalCount}.`}
          </span>
          {filters.geography === "moscow" && (
            <button
              className="text-link"
              onClick={() => patch({ geography: "all" })}
            >
              Включить Подмосковье <ArrowRight size={16} />
            </button>
          )}
        </div>
      )}
    </>
  );

  function renderEvent(e: ArtEvent) {
    const i = catalog!.institutions.find(
      (x) => x.institution_id === e.institution_id,
    )!;
    const isNew = e.first_detected_at > personal.previousVisit;
    return (
      <article
        className={`event-row ${personal.read.includes(e.event_id) ? "event-read" : ""}`}
        key={e.event_id}
      >
        <div className="event-date">
          <b>{dayLabel(e.start_date, { day: "2-digit", month: "2-digit" })}</b>
          <span>
            {e.start_time || dayLabel(e.start_date, { weekday: "short" })}
          </span>
          {e.end_date && e.end_date !== e.start_date && (
            <small>
              до{" "}
              {dayLabel(e.end_date, {
                day: "numeric",
                month: "short",
                ...(e.end_date.slice(0, 4) !== today.slice(0, 4)
                  ? { year: "numeric" }
                  : {}),
              })}
            </small>
          )}
        </div>
        <div className="event-body">
          <div className="event-kicker">
            <span>{EVENT_TYPES[e.event_type] || "Другое"}</span>
            {e.geography_scope === "moscow_region" && <span>Подмосковье</span>}
            {isNew && <span className="new-label">Новое</span>}
            {personal.read.includes(e.event_id) && (
              <Eye size={12} aria-label="Просмотрено" />
            )}
          </div>
          <button className="event-title" onClick={() => openEvent(e)}>
            {e.title}
          </button>
          <button
            className="venue-link"
            onClick={() => setSpaceId(i.institution_id)}
          >
            {i.name}
            {i.independent && (
              <span
                className="independent-dot"
                title="Независимое пространство"
              />
            )}
          </button>
          {e.description && <p>{e.description}</p>}
        </div>
        <div className="event-actions">
          <button
            className={`icon-button ${personal.saved.includes(e.event_id) ? "is-active" : ""}`}
            aria-label={
              personal.saved.includes(e.event_id)
                ? "Убрать событие из сохранённого"
                : "Сохранить событие"
            }
            aria-pressed={personal.saved.includes(e.event_id)}
            onClick={() => togglePersonal("saved", e.event_id)}
          >
            <Bookmark
              size={17}
              fill={
                personal.saved.includes(e.event_id) ? "currentColor" : "none"
              }
            />
          </button>
          <Ext
            href={e.primary_url}
            className="icon-button"
            title="Открыть первоисточник"
          >
            <ArrowUpRight size={19} />
            <span className="sr-only">Первоисточник: {e.title}</span>
          </Ext>
        </div>
      </article>
    );
  }
  function emptyEvents(day?: string) {
    return (
      <div className="empty-events">
        <div className="empty-copy">
          <span className="eyebrow">
            {activeCount || day
              ? "ПО ВАШЕМУ ЗАПРОСУ"
              : "В ОЖИДАНИИ ПОДТВЕРЖДЕНИЯ"}
          </span>
          <h3>
            {activeCount || day
              ? "Событий не найдено"
              : "Подтверждённых событий пока нет"}
          </h3>
          <p>
            {activeCount || day
              ? "На выбранные даты и с этими фильтрами подтверждённых событий нет. Попробуйте расширить поиск."
              : "События появятся после проверки публикаций. Пока можно открыть каталог и страницы пространств."}
          </p>
          {activeCount ? (
            <button className="text-link" onClick={reset}>
              Сбросить фильтры <ArrowRight size={16} />
            </button>
          ) : (
            <button className="text-link" onClick={() => navigate("spaces")}>
              Открыть каталог пространств <ArrowRight size={17} />
            </button>
          )}
        </div>
      </div>
    );
  }
  const filteredSources = (catalog?.sources || []).filter((s) => {
    const institutions = catalog!.institutions.filter((i) =>
      s.institution_ids.includes(i.institution_id),
    );
    return (
      (!sourceStatus || sourceMap.get(s.source_id)?.status === sourceStatus) &&
      (!filters.institution ||
        s.institution_ids.includes(filters.institution)) &&
      (!filters.scene ||
        institutions.some((i) =>
          filters.scene === "independent"
            ? i.independent
            : i.entity_type === "institution",
        )) &&
      (!filters.category ||
        institutions.some((i) => i.entity_type === filters.category)) &&
      (!filters.onlyFavorites ||
        s.institution_ids.some((id) => personal.favorites.includes(id))) &&
      (!filters.district ||
        institutions.some((i) => i.districts.includes(filters.district))) &&
      (!filters.q ||
        normalize(
          s.url +
            " " +
            institutions.map((i) => [i.name, ...i.aliases].join(" ")).join(" "),
        ).includes(normalize(filters.q)))
    );
  });
  const grouped: Record<string, ArtEvent[]> = {};
  for (const e of events) {
    const label = isOngoing(e, today)
      ? "Сейчас идут"
      : e.start_date === today
        ? "Сегодня"
        : e.start_date === plusDays(today, 1)
          ? "Завтра"
          : e.start_date < today
            ? "Архив"
            : e.start_date <=
                plusDays(
                  today,
                  6 - ((new Date(today + "T12:00Z").getUTCDay() + 6) % 7),
                )
              ? "На этой неделе"
              : "Позже";
    (grouped[label] ??= []).push(e);
  }

  return (
    <>
      <a className="skip-link" href="#main">
        К содержимому
      </a>
      <div className="site-shell">
        <header className="site-header">
          <h1>
            <button
              className="home-link"
              onClick={() => {
                navigate("agenda");
                reset();
              }}
              aria-label="Арт-календарь Москвы, главная"
            >
              {CONFIG.title}
            </button>
          </h1>
          <div className="header-right">
            <button
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label={
                theme === "dark"
                  ? "Включить светлую тему"
                  : "Включить тёмную тему"
              }
              aria-pressed={theme === "dark"}
            >
              {theme === "dark" ? <Sun size={22} /> : <Moon size={22} />}
              <span>{theme === "dark" ? "Светлая тема" : "Тёмная тема"}</span>
            </button>
            <span className="today-label">
              {dayLabel(today, {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
              <i />
              МСК
            </span>
            <button
              className={`saved-control ${filters.onlySaved ? "is-active" : ""}`}
              onClick={() => {
                navigate("agenda");
                patch({
                  onlySaved: !filters.onlySaved,
                  onlyFavorites: false,
                  period: "all",
                });
              }}
            >
              <Bookmark size={16} />
              <span>Сохранённое</span>
              <b>{pad(personal.saved.length)}</b>
            </button>
          </div>
        </header>
        <div className="metadata-bar">
          <div>
            <span
              className={`status-dot ${feed?.metadata.last_successful_update ? "green" : ""}`}
            />
            <span>
              Последнее обновление:{" "}
              <strong>{stamp(feed?.metadata.last_successful_update)}</strong>
            </span>
          </div>
          <div className="data-count">
            <span>
              Пространств <b>{monitorCount || "—"}</b>
            </span>
            <span>
              Источников <b>{catalog?.sources.length || "—"}</b>
            </span>
            <span>
              Событий <b>{feed?.events.length ?? "—"}</b>
            </span>
          </div>
          <button
            className="refresh-control"
            disabled={refreshing}
            onClick={() => void fetchData()}
          >
            <RefreshCw size={13} className={refreshing ? "spinning" : ""} />
            {refreshing ? "Загружаем…" : "Обновить данные"}
          </button>
        </div>
        <nav className="main-nav" aria-label="Основная навигация">
          <div>
            {NAV.map((n, index) => (
              <button
                key={n.id}
                className={view === n.id ? "active" : ""}
                onClick={() => navigate(n.id)}
                aria-current={view === n.id ? "page" : undefined}
              >
                <sup>{pad(index + 1)}</sup>
                {n.label}
                {n.id === "spaces" && (
                  <small>{catalog?.institutions.length || 0}</small>
                )}
              </button>
            ))}
          </div>
          <button className="my-spaces" onClick={setFavoriteView}>
            <Heart
              size={15}
              fill={filters.onlyFavorites ? "currentColor" : "none"}
            />
            <span>Мои пространства</span>
            <small>{personal.favorites.length}</small>
          </button>
        </nav>
        <main id="main">
          <div className="search-toolbar">
            <div className="search-field">
              <Search size={18} />
              <input
                aria-label="Поиск по афише и каталогу"
                placeholder={
                  view === "review"
                    ? "Найти публикацию, канал или пространство"
                    : view === "sources"
                      ? "Найти источник или пространство"
                      : view === "spaces"
                        ? "Найти пространство, имя или практику"
                        : "Найти событие, пространство или имя"
                }
                value={filters.q}
                onChange={(e) => patch({ q: e.target.value })}
              />
              {filters.q && (
                <button
                  className="icon-button"
                  aria-label="Очистить поиск"
                  onClick={() => patch({ q: "" })}
                >
                  <X size={16} />
                </button>
              )}
              <kbd>/</kbd>
            </div>
            <button
              className="mobile-filter-button"
              onClick={() => setMobileFilters(!mobileFilters)}
              aria-expanded={mobileFilters}
            >
              <SlidersHorizontal size={16} />
              Фильтры{activeCount > 0 && <b>{activeCount}</b>}
            </button>
            <span className="toolbar-note">
              <span className="tiny-dot" /> Время событий — московское
            </span>
          </div>
          {error && (
            <div className="error-banner" role="alert">
              <AlertCircle size={18} />
              <div>
                <strong>Не удалось обновить данные</strong>
                <p>{error}</p>
              </div>
              <button onClick={() => void fetchData()}>Повторить</button>
            </div>
          )}
          {!catalog && !error ? (
            <div className="loading-state" role="status">
              <RefreshCw size={23} className="spinning" />
              <h2>Собираем индекс…</h2>
              <p>Загружаем опубликованный каталог и афишу.</p>
            </div>
          ) : catalog && feed ? (
            <div className="workspace-layout">
              <aside
                className={`sidebar ${mobileFilters ? "mobile-open" : ""}`}
                aria-label="Фильтры"
              >
                <div className="sidebar-title">
                  <span className="eyebrow">ФИЛЬТРЫ</span>
                  <SlidersHorizontal size={14} />
                </div>
                <button
                  className={`scene-option ${!filters.scene ? "selected" : ""}`}
                  onClick={() => patch({ scene: "" })}
                >
                  <span>Все пространства</span>
                  <b>{catalog.institutions.length}</b>
                </button>
                <button
                  className={`scene-option ${filters.scene === "independent" ? "selected" : ""}`}
                  onClick={() =>
                    patch({
                      scene:
                        filters.scene === "independent" ? "" : "independent",
                    })
                  }
                >
                  <span>
                    <i className="independent-dot" />
                    Независимая сцена
                  </span>
                  <b>
                    {catalog.institutions.filter((i) => i.independent).length}
                  </b>
                </button>
                <button
                  className={`scene-option ${filters.scene === "institution" ? "selected" : ""}`}
                  onClick={() =>
                    patch({
                      scene:
                        filters.scene === "institution" ? "" : "institution",
                    })
                  }
                >
                  <span>Институции и музеи</span>
                  <b>
                    {
                      catalog.institutions.filter(
                        (i) => i.entity_type === "institution",
                      ).length
                    }
                  </b>
                </button>
                {(view === "agenda" || view === "calendar") && (
                  <>
                    {(view === "agenda" || view === "calendar") && (
                      <label className="select-label">
                        География
                        <select
                          value={filters.geography}
                          onChange={(e) => patch({ geography: e.target.value })}
                        >
                          <option value="moscow">Москва</option>
                          <option value="all">Москва и Подмосковье</option>
                          <option value="moscow_region">Подмосковье</option>
                        </select>
                      </label>
                    )}
                    <div className="filter-section">
                      <div className="eyebrow">ТИП СОБЫТИЯ</div>
                      {Object.entries(EVENT_TYPES).map(([id, label]) => (
                        <Toggle
                          key={id}
                          checked={filters.types.includes(id)}
                          onChange={() =>
                            patch({
                              types: filters.types.includes(id)
                                ? filters.types.filter((t) => t !== id)
                                : [...filters.types, id],
                            })
                          }
                        >
                          {label}
                        </Toggle>
                      ))}
                    </div>
                    <div className="filter-section">
                      <Toggle
                        checked={filters.onlyNew}
                        onChange={() => patch({ onlyNew: !filters.onlyNew })}
                      >
                        Новые с прошлого визита
                      </Toggle>
                      <Toggle
                        checked={filters.onlySaved}
                        onChange={() =>
                          patch({ onlySaved: !filters.onlySaved })
                        }
                      >
                        Сохранённые события
                      </Toggle>
                    </div>
                  </>
                )}
                <div className="filter-section">
                  <Toggle
                    checked={filters.onlyFavorites}
                    onChange={() =>
                      patch({ onlyFavorites: !filters.onlyFavorites })
                    }
                  >
                    Мои пространства <Heart size={12} />
                  </Toggle>
                  <label className="select-label">
                    Тип пространства
                    <select
                      value={filters.category}
                      onChange={(e) => patch({ category: e.target.value })}
                    >
                      <option value="">Все типы</option>
                      {Object.entries(CATEGORIES).map(([id, label]) => (
                        <option key={id} value={id}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="select-label">
                    Пространство
                    <select
                      value={filters.institution}
                      onChange={(e) => patch({ institution: e.target.value })}
                    >
                      <option value="">Все пространства</option>
                      {catalog.institutions.map((i) => (
                        <option key={i.institution_id} value={i.institution_id}>
                          {i.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="select-label">
                    Район
                    <select
                      value={filters.district}
                      onChange={(e) => patch({ district: e.target.value })}
                    >
                      <option value="">Все районы</option>
                      {[
                        ...new Set(
                          catalog.institutions.flatMap((i) => i.districts),
                        ),
                      ].map((d) => (
                        <option key={d}>{d}</option>
                      ))}
                    </select>
                  </label>
                  {!catalog.institutions.some(
                    (i) => i.districts.length > 0,
                  ) && (
                    <small className="field-note">
                      Районы в исходном каталоге не указаны.
                    </small>
                  )}
                </div>
                {(view === "agenda" || view === "calendar") && (
                  <>
                    <details className="date-details">
                      <summary>
                        Выбрать период <Plus size={13} />
                      </summary>
                      <label className="select-label">
                        С даты
                        <input
                          type="date"
                          lang="ru"
                          value={filters.from}
                          onChange={(e) =>
                            patch({ from: e.target.value, period: "all" })
                          }
                        />
                      </label>
                      <label className="select-label">
                        По дату
                        <input
                          type="date"
                          lang="ru"
                          min={filters.from}
                          value={filters.to}
                          onChange={(e) =>
                            patch({ to: e.target.value, period: "all" })
                          }
                        />
                      </label>
                      {filters.from &&
                        filters.to &&
                        filters.from > filters.to && (
                          <p className="field-note">
                            Конец периода должен быть позже начала.
                          </p>
                        )}
                    </details>
                    <MiniCalendar
                      month={month}
                      setMonth={setMonth}
                      selected={calendarDay || filters.from}
                      onSelect={(day) => {
                        setCalendarDay(day);
                        patch({ period: "all", from: day, to: day });
                      }}
                      events={feed.events}
                    />
                  </>
                )}
                {activeCount > 0 && (
                  <button className="reset-button" onClick={reset}>
                    <X size={13} />
                    Сбросить фильтры <span>{activeCount}</span>
                  </button>
                )}
              </aside>
              <section
                className="main-content"
                aria-label={NAV.find((n) => n.id === view)?.label || "Афиша"}
              >
                {(view === "agenda" || view === "calendar") && (
                  <>
                    <div className="content-topline">
                      <div className="period-tabs">
                        {PERIODS.map((p) => (
                          <button
                            className={filters.period === p.id ? "active" : ""}
                            key={p.id}
                            onClick={() => {
                              patch({ period: p.id, from: "", to: "" });
                              setCalendarDay("");
                            }}
                          >
                            {p.label}
                          </button>
                        ))}
                      </div>
                      <div className="view-toggle" aria-label="Вид афиши">
                        <button
                          aria-label="Список событий"
                          title="Список"
                          className={view === "agenda" ? "active" : ""}
                          onClick={() => navigate("agenda")}
                        >
                          <LayoutList size={17} />
                        </button>
                        <button
                          aria-label="Календарь событий"
                          title="Календарь"
                          className={view === "calendar" ? "active" : ""}
                          onClick={() => navigate("calendar")}
                        >
                          <CalendarDays size={17} />
                        </button>
                      </div>
                    </div>
                    <div className="section-heading">
                      <div>
                        <h2>
                          {view === "calendar"
                            ? "Календарь событий"
                            : filters.onlySaved
                              ? "Сохранённые события"
                              : PERIODS.find((p) => p.id === filters.period)
                                  ?.label || "Выбранный период"}{" "}
                          <sup>{pad(events.length)}</sup>
                        </h2>
                        <span className="subheading">
                          {filters.from
                            ? `${dayLabel(filters.from)}${filters.to && filters.to !== filters.from ? " — " + dayLabel(filters.to) : ""}`
                            : "Выставки, открытия и публичные программы"}
                        </span>
                      </div>
                      {view === "agenda" ? (
                        <label className="sort-select">
                          <span className="sr-only">Сортировка</span>
                          <select
                            value={filters.sort}
                            onChange={(e) => patch({ sort: e.target.value })}
                          >
                            <option value="date">По дате события</option>
                            <option value="new">По дате обнаружения</option>
                          </select>
                          <ChevronDown size={12} />
                        </label>
                      ) : (
                        <div className="calendar-mode">
                          <button
                            className={calendarMode === "month" ? "active" : ""}
                            onClick={() => setCalendarMode("month")}
                          >
                            Месяц
                          </button>
                          <button
                            className={calendarMode === "week" ? "active" : ""}
                            onClick={() => setCalendarMode("week")}
                          >
                            Неделя
                          </button>
                        </div>
                      )}
                    </div>
                    {filterSummary}
                    {view === "calendar" ? (
                      <>
                        <MiniCalendar
                          large
                          week={calendarMode === "week"}
                          month={month}
                          setMonth={setMonth}
                          selected={calendarDay}
                          onSelect={(day) => {
                            setCalendarDay(day);
                            setMonth(day.slice(0, 7) + "-01");
                            patch({ period: "all", from: day, to: day });
                          }}
                          events={datesInCalendar}
                        />
                        <div className="calendar-selection">
                          <span className="eyebrow">
                            {calendarDay
                              ? dayLabel(calendarDay, {
                                  weekday: "long",
                                  day: "numeric",
                                  month: "long",
                                })
                              : "СОБЫТИЯ ВЫБРАННОГО ПЕРИОДА"}
                          </span>
                          <b>{events.length}</b>
                        </div>
                        {events.length
                          ? events.map(renderEvent)
                          : emptyEvents(calendarDay)}
                      </>
                    ) : events.length ? (
                      filters.sort === "new" ? (
                        events.map(renderEvent)
                      ) : (
                        <div className="event-groups">
                          {[
                            "Сегодня",
                            "Завтра",
                            "На этой неделе",
                            "Позже",
                            "Сейчас идут",
                            "Архив",
                          ]
                            .filter((k) => grouped[k])
                            .map((k) => (
                              <section className="event-group" key={k}>
                                <h3>
                                  {k}
                                  <span>{grouped[k].length}</span>
                                </h3>
                                {grouped[k].map(renderEvent)}
                              </section>
                            ))}
                        </div>
                      )
                    ) : (
                      emptyEvents()
                    )}
                  </>
                )}
                {view === "spaces" && (
                  <>
                    <div className="section-heading directory-heading">
                      <div>
                        <span className="eyebrow">
                          КАТАЛОГ / МЕСТА И ИНИЦИАТИВЫ
                        </span>
                        <h2>
                          {filters.onlyFavorites
                            ? "Мои пространства"
                            : "Пространства Москвы"}{" "}
                          <sup>{pad(spaces.length)}</sup>
                        </h2>
                        <span className="subheading">
                          Институции, галереи, самоорганизации и поисковые сети
                        </span>
                      </div>
                      <label className="sort-select">
                        <span className="sr-only">Статус пространства</span>
                        <select
                          value={directoryState}
                          onChange={(e) => {
                            setDirectoryState(e.target.value);
                            setVisibleSpaces(18);
                          }}
                        >
                          <option value="">Все статусы</option>
                          {Object.entries(STATES).map(([id, label]) => (
                            <option key={id} value={id}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <ChevronDown size={12} />
                      </label>
                    </div>
                    {filterSummary}
                    <div className="directory-note">
                      <span className="tiny-dot" />
                      Независимые пространства — в начале индекса. В каталоге
                      сохранены и площадки без анонсов.
                    </div>
                    <div className="directory-table">
                      <div className="directory-table-head">
                        <span>ПРОСТРАНСТВО</span>
                        <span>ПРАКТИКА / СТАТУС</span>
                        <span>ИСТОЧНИКИ</span>
                        <span />
                      </div>
                      {spaces.slice(0, visibleSpaces).map((i, index) => {
                        const upcoming = feed.events.filter(
                          (e) =>
                            e.institution_id === i.institution_id &&
                            (e.end_date || e.start_date) >= today,
                        ).length;
                        const healthy = i.source_ids.filter(
                          (id) => sourceMap.get(id)?.status === "working",
                        ).length;
                        return (
                          <article
                            className="institution-row"
                            key={i.institution_id}
                          >
                            <div className="institution-name">
                              <span className="row-number">
                                {pad(index + 1)}
                              </span>
                              <div>
                                <button
                                  onClick={() => setSpaceId(i.institution_id)}
                                >
                                  {i.name}
                                </button>
                                <small>
                                  {i.locations.find((l) => l.address)
                                    ?.address ||
                                    i.location_notes ||
                                    "Адрес не подтверждён"}
                                </small>
                                {i.independent && (
                                  <span className="institution-kind">
                                    <i className="independent-dot" />
                                    {i.category === "artist_run"
                                      ? "Самоорганизация"
                                      : "Независимое пространство"}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="institution-practice">
                              <span>
                                {i.tags
                                  .slice(0, 2)
                                  .map((t) => TAGS[t] || t)
                                  .join(" · ") || "Практики не указаны"}
                              </span>
                              <small>
                                {STATES[i.monitor_state]}
                                {upcoming > 0 ? ` · Событий: ${upcoming}` : ""}
                              </small>
                            </div>
                            <button
                              className="source-count"
                              onClick={() => {
                                navigate("sources");
                                patch({ institution: i.institution_id, q: "" });
                              }}
                            >
                              <span
                                className={`status-dot ${healthy ? "green" : ""}`}
                              />
                              {i.source_ids.length}
                              <ArrowUpRight size={12} />
                            </button>
                            <button
                              className={`icon-button favorite-button ${personal.favorites.includes(i.institution_id) ? "is-active" : ""}`}
                              aria-label={`${personal.favorites.includes(i.institution_id) ? "Убрать из избранного" : "Добавить в избранное"}: ${i.name}`}
                              aria-pressed={personal.favorites.includes(
                                i.institution_id,
                              )}
                              onClick={() =>
                                togglePersonal("favorites", i.institution_id)
                              }
                            >
                              <Heart
                                size={17}
                                fill={
                                  personal.favorites.includes(i.institution_id)
                                    ? "currentColor"
                                    : "none"
                                }
                              />
                            </button>
                          </article>
                        );
                      })}
                    </div>
                    {!spaces.length && (
                      <div className="empty-directory">
                        <Search size={26} />
                        <h3>Пространства не найдены</h3>
                        <p>
                          {filters.onlyFavorites
                            ? "Добавьте площадки в избранное нажатием на сердечко."
                            : "Попробуйте другое название или сбросьте фильтры."}
                        </p>
                        <button className="text-link" onClick={reset}>
                          Показать все пространства <ArrowRight size={16} />
                        </button>
                      </div>
                    )}
                    {spaces.length > visibleSpaces && (
                      <button
                        className="load-more"
                        onClick={() => setVisibleSpaces((n) => n + 24)}
                      >
                        Показать ещё <Plus size={16} />
                        <small>Осталось {spaces.length - visibleSpaces}</small>
                      </button>
                    )}
                  </>
                )}
                {view === "review" && (
                  <ReviewQueue
                    catalog={catalog}
                    data={review}
                    error={reviewError}
                    filters={filters}
                    personal={personal}
                    reason={reviewReason}
                    setReason={setReviewReason}
                    filterSummary={filterSummary}
                    onRetry={() => void fetchData()}
                  />
                )}
                {view === "sources" && (
                  <>
                    <div className="section-heading directory-heading">
                      <div>
                        <span className="eyebrow">ЖУРНАЛ ПРОВЕРОК</span>
                        <h2>
                          Источники <sup>{filteredSources.length}</sup>
                        </h2>
                        <span className="subheading">
                          Последние проверки, ошибки доступа и найденные анонсы
                        </span>
                      </div>
                      <button
                        className="text-link"
                        onClick={() => setMethod(true)}
                      >
                        Как это работает <CircleHelp size={15} />
                      </button>
                    </div>
                    <div className="source-summary">
                      <div>
                        <b>{checkedCount}</b>
                        <span>Доступны для проверки</span>
                      </div>
                      <div>
                        <b>
                          {
                            feed.sources.filter((s) => s.status === "manual")
                              .length
                          }
                        </b>
                        <span>Требуют настройки доступа</span>
                      </div>
                      <div>
                        <b>
                          {
                            feed.sources.filter((s) =>
                              ["blocked", "broken", "unavailable"].includes(
                                s.status,
                              ),
                            ).length
                          }
                        </b>
                        <span>Недоступны сборщику</span>
                      </div>
                    </div>
                    <div className="source-toolbar">
                      <label className="sort-select">
                        <span className="sr-only">Статус источника</span>
                        <select
                          value={sourceStatus}
                          onChange={(e) => setSourceStatus(e.target.value)}
                        >
                          <option value="">Все статусы</option>
                          {Object.entries(STATUS).map(([id, label]) => (
                            <option key={id} value={id}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <ChevronDown size={12} />
                      </label>
                      <span>
                        Последняя попытка:{" "}
                        {stamp(feed.metadata.last_attempted_refresh)}
                      </span>
                    </div>
                    {filterSummary}
                    <div className="sources-table">
                      <div className="source-table-head">
                        <span>ПРОСТРАНСТВО / ИСТОЧНИК</span>
                        <span>СТАТУС</span>
                        <span>ПРОВЕРКА / НАЙДЕНО</span>
                      </div>
                      {filteredSources.map((s) => {
                        const h = sourceMap.get(s.source_id);
                        return (
                          <article className="source-row" key={s.source_id}>
                            <div>
                              <div className="source-institutions">
                                {s.institution_ids.map((id) => (
                                  <button
                                    key={id}
                                    onClick={() => setSpaceId(id)}
                                  >
                                    {
                                      catalog.institutions.find(
                                        (i) => i.institution_id === id,
                                      )?.name
                                    }
                                  </button>
                                ))}
                              </div>
                              <Ext href={s.url} className="source-url">
                                {PLATFORM[s.platform] || "Публичный источник"} ·{" "}
                                {s.url
                                  .replace(/^https?:\/\//, "")
                                  .replace(/\/$/, "")}
                                <ArrowUpRight size={12} />
                              </Ext>
                            </div>
                            <div>
                              <span
                                className={`health-label ${h?.status === "working" ? "health-good" : ""}`}
                              >
                                <i />
                                {STATUS[h?.status || "review"] ||
                                  "Требует проверки"}
                              </span>
                              {s.requires_identity_confirmation && (
                                <p className="source-error">
                                  Кандидат: принадлежность канала пока не
                                  подтверждена.
                                </p>
                              )}
                              {h?.error && (
                                <p className="source-error">{h.error}</p>
                              )}
                            </div>
                            <div className="source-check">
                              <span>
                                {h?.last_attempted_at
                                  ? stamp(h.last_attempted_at)
                                  : "Не проверялся"}
                              </span>
                              {h?.posts_seen !== undefined && (
                                <small>
                                  Прочитано публикаций: {h.posts_seen}
                                </small>
                              )}
                              <small>
                                Подтверждено: {h?.detected_events || 0}
                              </small>
                              {h?.last_successful_extraction && (
                                <small>
                                  Извлечено:{" "}
                                  {stamp(h.last_successful_extraction)}
                                </small>
                              )}
                            </div>
                          </article>
                        );
                      })}
                      {!filteredSources.length && (
                        <div className="empty-directory">
                          <h3>Источники не найдены</h3>
                          <button className="text-link" onClick={reset}>
                            Сбросить фильтры <ArrowRight size={15} />
                          </button>
                        </div>
                      )}
                    </div>
                    <div className="queue-entry">
                      <p>
                        Неподтверждённые публикации и источники-кандидаты
                        вынесены в отдельный раздел.
                      </p>
                      <button
                        className="outline-button"
                        onClick={() => navigate("review")}
                      >
                        Открыть очередь проверки <ArrowRight size={16} />
                      </button>
                    </div>
                    <div className="owner-panel">
                      <div>
                        <span className="eyebrow">ДЛЯ ВЛАДЕЛЬЦА КАЛЕНДАРЯ</span>
                        <h3>Проверить источники сейчас</h3>
                        <p>
                          Откройте рабочий процесс и выберите «Run workflow».
                          Нужен доступ к репозиторию. Обычное обновление
                          страницы не запускает сбор.
                        </p>
                      </div>
                      <Ext href={CONFIG.workflow} className="outline-button">
                        Запустить проверку источников <ArrowUpRight size={16} />
                      </Ext>
                    </div>
                  </>
                )}
              </section>
            </div>
          ) : null}
        </main>
        <footer className="site-footer">
          <button className="text-link" onClick={() => setMethod(true)}>
            Методология сбора <CircleHelp size={18} />
          </button>
          <Ext href={`https://github.com/${CONFIG.repository}`}>
            Исходный код <ArrowUpRight size={18} />
          </Ext>
        </footer>
      </div>
      {selectedEvent && catalog && (
        <Dialog title={selectedEvent.title} onClose={() => setEventId("")}>
          <div className="detail-kicker">
            {EVENT_TYPES[selectedEvent.event_type]} ·{" "}
            {dayLabel(selectedEvent.start_date, {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
            {selectedEvent.start_time && ` / ${selectedEvent.start_time} МСК`}
            {selectedEvent.end_date &&
              ` — ${dayLabel(selectedEvent.end_date, { day: "numeric", month: "long", year: "numeric" })}`}
          </div>
          <button
            className="detail-venue"
            onClick={() => {
              setEventId("");
              setSpaceId(selectedEvent.institution_id);
            }}
          >
            {
              catalog.institutions.find(
                (i) => i.institution_id === selectedEvent.institution_id,
              )?.name
            }
            <ArrowUpRight size={17} />
          </button>
          {selectedEvent.date_basis === "publication_context" && (
            <p className="field-note">
              Год определён по контексту публикации. Уточняйте даты в
              оригинальном анонсе.
            </p>
          )}
          {selectedEvent.description && (
            <p className="detail-description">{selectedEvent.description}</p>
          )}
          {eventAddress && (
            <p className="detail-address">
              {eventAddress}
              {!selectedEvent.address && (
                <small className="field-note">
                  Адрес из исходного каталога. Актуальность уточняйте у
                  пространства.
                </small>
              )}
            </p>
          )}
          <Ext className="solid-button" href={selectedEvent.primary_url}>
            Оригинальный анонс <ArrowUpRight size={17} />
          </Ext>
          <div className="detail-actions">
            <button
              className="outline-button"
              onClick={() => togglePersonal("saved", selectedEvent.event_id)}
            >
              <Bookmark size={15} />
              {personal.saved.includes(selectedEvent.event_id)
                ? "Сохранено"
                : "Сохранить"}
            </button>
            <button
              className="outline-button"
              onClick={() =>
                downloadICS(
                  selectedEvent,
                  catalog.institutions.find(
                    (i) => i.institution_id === selectedEvent.institution_id,
                  )!,
                )
              }
            >
              <Download size={15} />В календарь
            </button>
            <button
              className="outline-button"
              onClick={() => {
                if (navigator.clipboard)
                  void navigator.clipboard.writeText(location.href).then(
                    () => notify("Ссылка на событие скопирована."),
                    () => notify("Скопируйте ссылку из адресной строки."),
                  );
                else notify("Скопируйте ссылку из адресной строки.");
              }}
            >
              <Link size={15} />
              Поделиться
            </button>
          </div>
          <div className="evidence-block">
            <span className="eyebrow">ИСТОЧНИКИ И ПРОВЕРКА</span>
            {selectedEvent.evidence.map((e, index) => (
              <Ext href={e.url} key={index}>
                {e.url}
                <ArrowUpRight size={13} />
              </Ext>
            ))}
            <p>
              Обнаружено: {stamp(selectedEvent.first_detected_at)}
              <br />
              Обновлено: {stamp(selectedEvent.last_updated_at)}
              <br />
              Доступность ссылки:{" "}
              {selectedEvent.link_status === "available"
                ? "подтверждена"
                : STATUS[selectedEvent.link_status] || "не подтверждена"}
              {selectedEvent.link_checked_at &&
                ` (${stamp(selectedEvent.link_checked_at)})`}
            </p>
          </div>
        </Dialog>
      )}
      {selectedSpace && catalog && feed && (
        <Dialog title={selectedSpace.name} onClose={() => setSpaceId("")} wide>
          <div className="detail-kicker">
            {selectedSpace.independent ? "Независимая сцена" : "Институция"} /{" "}
            {STATES[selectedSpace.monitor_state]}
          </div>
          {selectedSpace.aliases.length > 0 && (
            <p className="aliases">
              Также: {selectedSpace.aliases.join(" · ")}
            </p>
          )}
          <p className="detail-description">{selectedSpace.focus}</p>
          <div className="tags">
            {selectedSpace.tags.map((t) => (
              <span key={t}>{TAGS[t] || t}</span>
            ))}
          </div>
          <button
            className={`outline-button ${personal.favorites.includes(selectedSpace.institution_id) ? "is-active" : ""}`}
            onClick={() =>
              togglePersonal("favorites", selectedSpace.institution_id)
            }
          >
            <Heart
              size={15}
              fill={
                personal.favorites.includes(selectedSpace.institution_id)
                  ? "currentColor"
                  : "none"
              }
            />
            {personal.favorites.includes(selectedSpace.institution_id)
              ? "В моих пространствах"
              : "В мои пространства"}
          </button>
          <div className="space-detail-grid">
            <section>
              <span className="eyebrow">АДРЕС / ИСХОДНЫЙ КАТАЛОГ</span>
              {selectedSpace.locations.length ? (
                selectedSpace.locations.map((l) => (
                  <p key={l.location_id}>
                    {l.address || l.label}
                    {l.address_status !== "verified" && (
                      <small className="field-note">
                        Актуальность адреса уточняйте у пространства.
                      </small>
                    )}
                  </p>
                ))
              ) : (
                <p>{selectedSpace.location_notes || "Адрес не подтверждён"}</p>
              )}
            </section>
            <section>
              <span className="eyebrow">ЗА ЧЕМ СЛЕДИТЬ</span>
              <p>{selectedSpace.watch_for || "Программа уточняется."}</p>
            </section>
          </div>
          <section className="detail-sources">
            <h3>
              Источники <sup>{selectedSpace.source_ids.length}</sup>
            </h3>
            {selectedSpace.source_ids.map((id) => {
              const s = catalog.sources.find((x) => x.source_id === id);
              const h = sourceMap.get(id);
              return s ? (
                <div key={id}>
                  <Ext href={s.url}>
                    {PLATFORM[s.platform] || "Источник"}
                    <ArrowUpRight size={15} />
                    <span>{s.url}</span>
                  </Ext>
                  <small>
                    {STATUS[h?.status || "review"]} ·{" "}
                    {stamp(h?.last_attempted_at)}
                  </small>
                </div>
              ) : null;
            })}
          </section>
          <section className="space-events">
            <h3>Предстоящие и текущие события</h3>
            {feed.events.filter(
              (e) =>
                e.institution_id === selectedSpace.institution_id &&
                (e.end_date || e.start_date) >= today,
            ).length ? (
              feed.events
                .filter(
                  (e) =>
                    e.institution_id === selectedSpace.institution_id &&
                    (e.end_date || e.start_date) >= today,
                )
                .map((e) => (
                  <button
                    key={e.event_id}
                    onClick={() => {
                      setSpaceId("");
                      openEvent(e);
                    }}
                  >
                    {dayLabel(e.start_date)} · {e.title}
                    <ArrowRight size={16} />
                  </button>
                ))
            ) : (
              <p className="field-note">
                Подтверждённых анонсов пока нет. Пространство остаётся в
                каталоге независимо от наличия событий.
              </p>
            )}
          </section>
        </Dialog>
      )}
      {((eventId && !selectedEvent && feed) ||
        (spaceId && !selectedSpace && catalog)) && (
        <Dialog
          title="Запись не найдена"
          onClose={() => {
            setEventId("");
            setSpaceId("");
          }}
        >
          <p>
            В опубликованном наборе данных нет этой записи. Она могла быть
            удалена редактором.
          </p>
        </Dialog>
      )}
      {method && (
        <Dialog title="Методология сбора" onClose={() => setMethod(false)} wide>
          <div className="detail-kicker">О ПРОЕКТЕ / ПРИНЦИПЫ МОНИТОРИНГА</div>
          <p className="detail-description">
            Арт-календарь Москвы — открытый индекс современного искусства. Мы
            собираем публичные анонсы институций, галерей и самоорганизаций,
            сохраняя ссылку на оригинальную публикацию.
          </p>
          <div className="method-list">
            <section>
              <span>01</span>
              <div>
                <h3>От первоисточника к событию</h3>
                <p>
                  В афишу попадают анонсы с подтверждённой датой и отдельной
                  страницей события. Неуверенные результаты остаются в разделе
                  «На проверке»: там видны исходный текст, ссылка и причина
                  остановки. Это список для ручного разбора; публикация требует
                  редакторской правки в репозитории. Автоматического одобрения и
                  назначенного редактора сейчас нет.
                </p>
                <button
                  className="text-link"
                  onClick={() => {
                    setMethod(false);
                    navigate("review");
                  }}
                >
                  Открыть очередь проверки <ArrowRight size={16} />
                </button>
              </div>
            </section>
            <section>
              <span>02</span>
              <div>
                <h3>Примерно раз в три дня</h3>
                <p>
                  Ежедневное расписание проверяет, прошло ли 72 часа с
                  завершённого сбора. Фактическое время успешного обновления
                  всегда указано на сайте. Запуск может задерживаться; при сбоях
                  прежние события сохраняются.
                </p>
              </div>
            </section>
            <section>
              <span>03</span>
              <div>
                <h3>Охват всегда неполный</h3>
                <p>
                  Закрытые публикации, ограничения соцсетей и недоступные сайты
                  оставляют пробелы. Публичные Телеграм-публикации читаются из
                  открытых лент или через авторизованный API. Для Инстаграма
                  нужен официальный API; локальные экспорты направляются на
                  редакционную проверку. Даты и условия посещения уточняйте в
                  оригинальном анонсе.
                </p>
              </div>
            </section>
            <section>
              <span>04</span>
              <div>
                <h3>Личный архив без регистрации</h3>
                <p>
                  Избранные пространства, сохранённые события и отметки
                  просмотра хранятся только в этом браузере. Данные не
                  синхронизируются между устройствами. Очистка данных браузера
                  удалит ваш архив.
                </p>
              </div>
            </section>
          </div>
          <div className="method-stats">
            <span>
              <b>{catalog?.institutions.length || 0}</b> записей каталога
            </span>
            <span>
              <b>{monitorCount}</b> в мониторинге
            </span>
            <span>
              <b>{catalog?.sources.length || 0}</b> первоисточника
            </span>
          </div>
          <Ext href={CONFIG.workflow} className="outline-button">
            Владельцу: запустить проверку источников <ArrowUpRight size={15} />
          </Ext>
        </Dialog>
      )}
      {toast && (
        <div className="toast" role="status">
          <CheckCheck size={18} />
          <span>{toast}</span>
          <button
            className="icon-button"
            onClick={() => setToast("")}
            aria-label="Закрыть уведомление"
          >
            <X size={15} />
          </button>
        </div>
      )}
    </>
  );
}
