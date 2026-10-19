import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { ArrowUpRight } from "lucide-react";
import type { Catalog, Filters, Personal, ReviewData } from "./types";
import { filterInstitutions, normalize, stamp, dayLabel, safeDay } from "./lib";
import { CONFIG, EVENT_TYPES } from "./config";
import { Ext } from "./ExternalLink";

const repo = `https://github.com/${CONFIG.repository}`;

export function ReviewQueue({
  catalog,
  data,
  error,
  filters,
  personal,
  reason,
  setReason,
  filterSummary,
  onRetry,
}: {
  catalog: Catalog;
  data: ReviewData | null;
  error: string;
  filters: Filters;
  personal: Personal;
  reason: string;
  setReason: (value: string) => void;
  filterSummary: ReactNode;
  onRetry: () => void;
}) {
  const [limit, setLimit] = useState(25);
  const [section, setSection] = useState("publications");
  useEffect(() => setLimit(25), [filters, reason, data]);
  const matched = new Set(
    filterInstitutions(
      catalog.institutions,
      { ...filters, q: "" },
      personal,
    ).map((i) => i.institution_id),
  );
  const hasInstitutionFilter = !!(
    filters.institution ||
    filters.category ||
    filters.scene ||
    filters.district ||
    filters.onlyFavorites
  );
  const sourceMap = new Map(catalog.sources.map((s) => [s.source_id, s]));
  const names = (ids: string[]) =>
    catalog.institutions
      .filter((i) => ids.includes(i.institution_id))
      .map((i) => [i.name, ...i.aliases].join(" / "))
      .join("; ");
  const query = normalize(filters.q);
  const candidates = catalog.sources.filter(
    (s) =>
      s.requires_identity_confirmation &&
      (!hasInstitutionFilter ||
        s.institution_ids.some((id) => matched.has(id))) &&
      (!query ||
        normalize(
          `${s.url} ${names(s.institution_ids)} ${s.discovery?.profile_title || ""}`,
        ).includes(query)),
  );
  const items = (data?.items || []).filter((item) => {
    const source = sourceMap.get(item.source_id || "");
    const ids = item.candidate?.institution_id
      ? [item.candidate.institution_id]
      : source?.institution_ids || [];
    return (
      (!hasInstitutionFilter || ids.some((id) => matched.has(id))) &&
      (!reason || item.reason === reason) &&
      (!query ||
        normalize(
          [
            item.candidate?.title,
            item.candidate?.description,
            item.candidate?.primary_url,
            source?.url,
            names(ids),
            item.reason,
          ].join(" "),
        ).includes(query))
    );
  });
  const reasons = [
    ...new Set(data?.items.map((item) => item.reason) || []),
  ].sort((a, b) => a.localeCompare(b, "ru"));
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>На проверке</h2>
          <span className="subheading">
            Источники-кандидаты и тексты без достаточной календарной привязки
          </span>
        </div>
      </div>
      <div className="source-toolbar">
        <label className="select-label">
          Причина остановки публикации
          <select value={reason} onChange={(e) => setReason(e.target.value)}>
            <option value="">Все причины</option>
            {reasons.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <span>Снимок очереди: {stamp(data?.generated_at)}</span>
      </div>
      {filterSummary}
      <p className="field-note">
        Просмотр без редактирования. Решения вносятся через репозиторий
        владельцем сайта.
      </p>
      <details className="review-guide">
        <summary>Как разобрать очередь</summary>
        <p>
          Предварительные события уже публикуются в афише с пометками о датах и
          местах. Здесь остаются тексты, из которых не удалось выделить событие
          или календарную дату. Для редакторских правок нужен доступ к
          репозиторию.
        </p>
        <ol>
          <li>
            Для источника-кандидата найдите ссылку на канал с официального сайта
            или другого подтверждённого аккаунта площадки. Совпадения названия
            недостаточно. Сохраните доказательство принадлежности в каталоге
            источников.
          </li>
          <li>
            Для публикации откройте оригинал, уточните название, площадку, даты,
            адрес и тип события. В очереди бывают новости и другие тексты,
            которые вообще не являются анонсами.
          </li>
          <li>
            Подтверждённое событие добавьте в <code>manual_events</code>{" "}
            редакторских правок; затем запустите сбор. Само исправление файла
            без запуска сборщика не добавит событие в афишу.
          </li>
        </ol>
        <div className="review-links">
          <Ext href={`${repo}/blob/main/docs/editorial-review.md`}>
            Пошаговая инструкция <ArrowUpRight size={16} />
          </Ext>
          <Ext href={`${repo}/edit/main/editorial/overrides.json`}>
            Редакторские правки в GitHub <ArrowUpRight size={16} />
          </Ext>
          <Ext href={CONFIG.workflow}>
            Запустить сбор <ArrowUpRight size={16} />
          </Ext>
        </div>
      </details>
      <div className="review-tabs" aria-label="Раздел очереди">
        <button
          aria-pressed={section === "publications"}
          onClick={() => setSection("publications")}
        >
          Публикации <sup>{data ? items.length : "—"}</sup>
        </button>
        <button
          aria-pressed={section === "sources"}
          onClick={() => setSection("sources")}
        >
          Источники-кандидаты <sup>{candidates.length}</sup>
        </button>
      </div>
      <section
        aria-label="Источники-кандидаты"
        className="review-section"
        hidden={section !== "sources"}
      >
        <h3>
          Подтвердить принадлежность каналов <sup>{candidates.length}</sup>
        </h3>
        <p className="field-note">
          Принадлежность каналов нужно уточнить. Включён режим публикации
          предварительных событий с пометками о неопределённости. Фильтр причин
          ниже относится только к публикациям.
        </p>
        {candidates.map((source) => (
          <article className="review-card" key={source.source_id}>
            <h4>
              {source.discovery?.profile_title || names(source.institution_ids)}
            </h4>
            <p>{names(source.institution_ids)}</p>
            <p className="review-reason">
              Не хватает внешнего подтверждения принадлежности канала.
            </p>
            <Ext href={source.url}>
              {source.url} <ArrowUpRight size={16} />
            </Ext>
            <details>
              <summary>Основание добавления и следующий шаг</summary>
              <p>{source.access_notes}</p>
              {source.discovery?.evidence?.map((evidence, index) => (
                <p key={index}>
                  {evidence.page_url && (
                    <Ext href={evidence.page_url}>
                      Текущее подтверждение <ArrowUpRight size={14} />
                    </Ext>
                  )}
                  {evidence.context && (
                    <span className="review-text">{evidence.context}</span>
                  )}
                </p>
              ))}
              <p>
                Найдите внешнюю ссылку на этот канал, добавьте её и дату
                проверки в каталог. После подтверждения проверьте роль связи с
                пространством — снятия одного флага кандидата недостаточно.
              </p>
              <Ext href={`${repo}/edit/main/catalog/additional-sources.json`}>
                Открыть каталог в GitHub <ArrowUpRight size={16} />
              </Ext>
            </details>
            <small className="review-id">
              {source.source_id} · проверено{" "}
              {stamp(source.discovery?.verified_at)}
            </small>
          </article>
        ))}
        {!candidates.length && (
          <p>По выбранным фильтрам источников-кандидатов нет.</p>
        )}
      </section>
      <section
        aria-label="Публикации на проверке"
        className="review-section"
        hidden={section !== "publications"}
      >
        <h3>
          Разобрать публикации <sup>{data ? items.length : "—"}</sup>
        </h3>
        <p className="field-note">
          Это кандидаты на события. Даты и названия ниже не подтверждены; текст
          может быть сокращён сборщиком.
        </p>
        {error && (
          <div role="alert" className="review-card">
            <p>{error}</p>
            <button className="outline-button" onClick={onRetry}>
              Повторить загрузку очереди
            </button>
          </div>
        )}
        {items.slice(0, limit).map((item, index) => {
          const source = sourceMap.get(item.source_id || "");
          const candidate = item.candidate || {};
          const ids = candidate.institution_id
            ? [candidate.institution_id]
            : source?.institution_ids || [];
          return (
            <article
              className="review-card"
              key={`${item.source_id}-${candidate.primary_url}-${index}`}
            >
              <p className="review-reason">{item.reason}</p>
              <h4>
                {candidate.title || "Публикация без выделенного названия"}
              </h4>
              <p>
                {ids.length
                  ? `Связанные пространства: ${names(ids)}`
                  : "Пространство не определено"}
              </p>
              {safeDay(candidate.start_date || null) && (
                <p>
                  Предположительная дата:{" "}
                  {dayLabel(candidate.start_date!, {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                  {candidate.start_time && `, ${candidate.start_time}`}
                  {safeDay(candidate.end_date || null) &&
                    ` — ${dayLabel(candidate.end_date!, { day: "numeric", month: "long", year: "numeric" })}`}
                </p>
              )}
              {candidate.event_type && (
                <p>
                  Предположительный тип:{" "}
                  {EVENT_TYPES[candidate.event_type] || candidate.event_type}
                </p>
              )}
              {candidate.address && (
                <p>Адрес из публикации: {candidate.address}</p>
              )}
              {candidate.description && (
                <details>
                  <summary>Прочитать извлечённый текст</summary>
                  <p className="review-text">{candidate.description}</p>
                </details>
              )}
              <div className="review-links">
                {candidate.primary_url && (
                  <Ext href={candidate.primary_url}>
                    Оригинальная публикация <ArrowUpRight size={16} />
                  </Ext>
                )}
                {source && (
                  <Ext href={source.url}>
                    Источник <ArrowUpRight size={16} />
                  </Ext>
                )}
              </div>
              <small className="review-id">
                {item.source_id || "Редакторская запись"}
                {ids.length > 0 && ` · ${ids.join(", ")}`}
                {candidate.published_at &&
                  ` · опубликовано ${stamp(candidate.published_at)}`}
              </small>
            </article>
          );
        })}
        {data && !items.length && (
          <p>По выбранным фильтрам публикаций на проверке нет.</p>
        )}
        {items.length > limit && (
          <button
            className="outline-button"
            onClick={() => setLimit((value) => value + 25)}
          >
            Показать ещё · осталось {items.length - limit}
          </button>
        )}
      </section>
      <a
        className="text-link"
        href={`${import.meta.env.BASE_URL}data/review.json`}
        download="review.json"
      >
        Скачать очередь в JSON
      </a>
    </>
  );
}
