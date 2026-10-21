export interface Institution {
  institution_id: string;
  name: string;
  aliases: string[];
  tags: string[];
  source_ids: string[];
  entity_type: string;
  monitor_state: string;
  independent: boolean;
  category: string;
  monitoring_priority: string;
  focus: string;
  watch_for: string;
  location_notes: string;
  districts: string[];
  locations: {
    location_id: string;
    label: string;
    address?: string;
    address_status?: string;
    city?: string;
  }[];
  operating_status: string;
  monitor_notes: string;
}
export interface Source {
  source_id: string;
  url: string;
  platform: string;
  institution_ids: string[];
  roles: string[];
  requires_identity_confirmation?: boolean;
  editor_approved_on?: string;
  access_notes?: string;
  discovery?: {
    profile_title?: string;
    verified_at?: string;
    evidence?: { page_url?: string; context?: string; checked_at?: string }[];
  };
}
export interface Health {
  source_id: string;
  status: string;
  adapter?: string;
  posts_seen?: number;
  last_attempted_at?: string;
  last_successful_extraction?: string;
  last_successful_check?: string;
  tentative_events?: number;
  detected_events: number;
  new_events: number;
  error?: string;
}
export interface ArtEvent {
  event_id: string;
  merged_event_ids?: string[];
  institution_id: string;
  title: string;
  venue_name?: string;
  venue_is_tentative?: boolean;
  review_status?: "verified" | "tentative";
  uncertainties?: string[];
  event_type: string;
  start_date: string;
  end_date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  primary_url: string;
  description?: string;
  address?: string;
  source_platform: string;
  first_detected_at: string;
  last_seen_at: string;
  last_updated_at: string;
  published_at?: string;
  confidence?: string;
  geography_scope?: "moscow" | "moscow_region" | null;
  city?: string | null;
  date_basis?: string;
  verification_method?: string;
  link_status: string;
  link_checked_at?: string;
  registration_url?: string;
  parent_event_id?: string;
  evidence: {
    url: string;
    status: string;
    checked_at?: string;
    title?: string;
    title_basis?: string;
    start_date?: string;
    end_date?: string | null;
    start_time?: string | null;
  }[];
}
export interface Catalog {
  institutions: Institution[];
  sources: Source[];
  metadata: { updated_on: string; counts: Record<string, number> };
  tags: { tag_id: string; label_ru: string }[];
}
export interface Feed {
  metadata: {
    last_successful_update?: string | null;
    last_attempted_refresh?: string;
    last_completed_refresh?: string;
    generated_at: string;
    source_count: number;
    event_count: number;
    review_count: number;
    tentative_count?: number;
    last_editorial_update?: string;
    partial: boolean;
    run_status: string;
    successful_sources_this_run: number;
  };
  events: ArtEvent[];
  sources: Health[];
}
export interface Filters {
  q: string;
  period: string;
  types: string[];
  institution: string;
  district: string;
  category: string;
  scene: string;
  onlyNew: boolean;
  onlySaved: boolean;
  onlyFavorites: boolean;
  sort: string;
  from: string;
  to: string;
}
export interface Personal {
  favorites: string[];
  saved: string[];
  read: string[];
  previousVisit: string;
}

export interface ReviewItem {
  source_id?: string;
  candidate?: Partial<ArtEvent>;
  reason: string;
  link_status?: string;
}
export interface ReviewData {
  generated_at: string;
  items: ReviewItem[];
}
