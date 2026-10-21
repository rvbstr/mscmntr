import { describe, it, expect } from "vitest";
import {
  DEFAULT_FILTERS,
  eventICS,
  eventLastDay,
  filterEvents,
  filterInstitutions,
  moscowToday,
  safeDay,
  filtersFromURL,
} from "./lib";
import type { ArtEvent, Institution, Personal } from "./types";
import { vi } from "vitest";

it("selects openings initially and preserves explicit all-types and exhibition URLs", () => {
  for (const [search, types] of [
    ["", ["opening"]],
    ["?type=all", []],
    ["?type=", []],
    ["?type=exhibition", ["exhibition"]],
  ] as const) {
    vi.stubGlobal("location", { search });
    expect(filtersFromURL().types).toEqual(types);
  }
  vi.unstubAllGlobals();
});
const institution = {
  institution_id: "A",
  name: "Иваний галерея",
  aliases: ["IVANY GALLERY"],
  tags: ["artist_run"],
  independent: true,
  districts: [],
  locations: [],
} as unknown as Institution;
const personal: Personal = {
  favorites: ["A"],
  saved: ["E"],
  read: [],
  previousVisit: "2026-10-15T12:00:00Z",
};
const event = {
  event_id: "E",
  institution_id: "A",
  title: "Проверка",
  event_type: "exhibition",
  start_date: "2026-10-17",
  end_date: "2026-10-21",
  primary_url: "https://example.org/exhibitions/a",
  first_detected_at: "2026-10-16T12:00:00Z",
} as ArtEvent;
it("opening ranges affect only their first day, while the exhibition remains ongoing", () => {
  const opening = { ...event, event_type: "opening" } as ArtEvent;
  const day = { ...DEFAULT_FILTERS, period: "all", from: "2026-10-20", to: "2026-10-20" };
  expect(eventLastDay(opening)).toBe("2026-10-17");
  expect(filterEvents([opening, event], [institution], day, personal)).toEqual([event]);
  expect(filterEvents([opening], [institution], { ...day, from: "2026-10-17", to: "2026-10-17" }, personal)).toHaveLength(1);
  expect(eventICS(opening, institution)).toContain("DTEND;VALUE=DATE:20261018");
  expect(eventICS(event, institution)).toContain("DTEND;VALUE=DATE:20261022");
});
describe("filters and dates", () => {
  it("rejects malformed dates in shared URLs", () => {
    expect(safeDay("nonsense")).toBe("");
    expect(safeDay("2026-02-31")).toBe("");
    expect(safeDay("2026-10-17")).toBe("2026-10-17");
  });
  it("uses Moscow date across UTC midnight", () =>
    expect(moscowToday(new Date("2026-10-15T22:00:00Z"))).toBe("2026-10-16"));
  it("searches Latin aliases and combines favorites, scene and dates", () =>
    expect(
      filterEvents(
        [event],
        [institution],
        {
          ...DEFAULT_FILTERS,
          q: "ivany",
          scene: "independent",
          onlyFavorites: true,
          onlySaved: true,
          onlyNew: true,
          from: "2026-10-18",
          to: "2026-10-20",
        },
        personal,
        "2026-10-16",
      ),
    ).toHaveLength(1));
  it("excludes nonmatching event type", () =>
    expect(
      filterEvents(
        [event],
        [institution],
        { ...DEFAULT_FILTERS, types: ["opening"] },
        personal,
        "2026-10-16",
      ),
    ).toHaveLength(0));
  it("distinguishes ongoing from upcoming", () => {
    expect(
      filterEvents(
        [event],
        [institution],
        { ...DEFAULT_FILTERS, period: "ongoing" },
        personal,
        "2026-10-16",
      ),
    ).toHaveLength(0);
    expect(
      filterEvents(
        [event],
        [institution],
        { ...DEFAULT_FILTERS, period: "ongoing" },
        personal,
        "2026-10-18",
      ),
    ).toHaveLength(1);
  });
  it("keeps institutions with no events and searches aliases", () =>
    expect(
      filterInstitutions(
        [institution],
        { ...DEFAULT_FILTERS, q: "ivany" },
        personal,
      ),
    ).toHaveLength(1));
  it("uses inclusive exhibition end and exclusive calendar end", () =>
    expect(eventICS(event, institution)).toContain(
      "DTEND;VALUE=DATE:20261022",
    ));
  it("converts Moscow opening times to UTC", () =>
    expect(eventICS({ ...event, start_time: "18:00" }, institution)).toContain(
      "DTSTART:20261017T150000Z",
    ));
  it("escapes text and prevents iCalendar line injection", () => {
    const output = eventICS(
      { ...event, title: "Текст, название;\nBEGIN:BAD" },
      institution,
    );
    expect(output).toContain("SUMMARY:Текст\\, название\\;\\nBEGIN:BAD");
    expect(output).not.toContain("\r\nBEGIN:BAD");
  });
  it("filters archive and never treats a finished exhibition as current", () => {
    expect(
      filterEvents(
        [event],
        [institution],
        { ...DEFAULT_FILTERS },
        personal,
        "2026-10-23",
      ),
    ).toHaveLength(0);
    expect(
      filterEvents(
        [event],
        [institution],
        { ...DEFAULT_FILTERS, period: "archive" },
        personal,
        "2026-10-23",
      ),
    ).toHaveLength(1);
  });
});

describe("geography of public announcements", () => {
  it("shows all catalogued locations together by default", () => {
    const regional = {
      ...event,
      event_id: "regional",
      geography_scope: "moscow_region" as const,
    };
    expect(
      filterEvents(
        [event, regional],
        [institution],
        { ...DEFAULT_FILTERS },
        personal,
        "2026-10-16",
      ),
    ).toHaveLength(2);
  });
});

it("exports provisional dates and places explicitly as tentative in iCalendar", () => {
  const output = eventICS(
    {
      ...event,
      review_status: "tentative",
      venue_is_tentative: true,
      uncertainties: ["Дата начала предположительная"],
    },
    institution,
  ).replaceAll("\r\n ", "");
  expect(output).toContain("STATUS:TENTATIVE");
  expect(output).toContain("SUMMARY:[Предварительно]");
  expect(output).toContain("LOCATION:Место уточняется");
  expect(output).toContain("Дата начала предположительная");
});

it("exports the event's branch instead of the first address of a multi-site museum", () => {
  const museum = {
    ...institution,
    locations: [
      { address: "Петровка, 25" },
      { address: "Гоголевский бульвар, 10" },
    ],
  } as unknown as Institution;
  const output = eventICS(
    { ...event, venue_name: "ММОМА, Гоголевский 10" },
    museum,
  ).replaceAll("\r\n ", "");
  expect(output).toContain("Гоголевский 10");
  expect(output).not.toContain("Петровка");
});
