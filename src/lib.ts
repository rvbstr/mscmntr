import type { ArtEvent, Filters, Institution, Personal } from './types';
import { CONFIG } from './config';
export const normalize = (value: string) => value.toLocaleLowerCase('ru').replaceAll('ё','е').normalize('NFKC').replace(/[’'«»—–-]/g,' ');
export function moscowToday(now = new Date()) { return new Intl.DateTimeFormat('en-CA', {timeZone: CONFIG.timezone,year:'numeric',month:'2-digit',day:'2-digit'}).format(now); }
export function plusDays(day: string, n: number) { const d = new Date(`${day}T12:00:00Z`); d.setUTCDate(d.getUTCDate()+n); return d.toISOString().slice(0,10); }
export function dayLabel(day: string, options: Intl.DateTimeFormatOptions = {day:'numeric',month:'long'}) { return new Intl.DateTimeFormat('ru-RU', {...options,timeZone:CONFIG.timezone}).format(new Date(`${day}T12:00:00+03:00`)); }
export function stamp(iso?: string | null) { return iso ? new Intl.DateTimeFormat('ru-RU',{timeZone:CONFIG.timezone,day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'}).format(new Date(iso)) : 'Пока не было'; }
export const isOngoing = (e: ArtEvent, today: string) => e.event_type==='exhibition' && e.start_date<=today && !!e.end_date && e.end_date>=today;
export function safeDay(value: string | null): string {
  if(!value||!/^\d{4}-\d{2}-\d{2}$/.test(value))return '';
  try{return new Date(value+'T12:00:00Z').toISOString().slice(0,10)===value?value:'';}catch{return '';}
}
export function filtersFromURL(): Filters {
  const p = new URLSearchParams(location.search);
  return {q:p.get('q')||'',period:['upcoming','today','tomorrow','week','ongoing','archive','all'].includes(p.get('period')||'')?p.get('period')!:'upcoming',types:(p.get('type')||'').split(',').filter(Boolean),institution:p.get('institution')||'',district:p.get('district')||'',category:p.get('category')||'',scene:p.get('scene')||'',onlyNew:p.get('new')==='1',onlySaved:p.get('saved')==='1',onlyFavorites:p.get('favorites')==='1',sort:p.get('sort')==='new'?'new':'date',from:safeDay(p.get('from')),to:safeDay(p.get('to'))};
}
export const DEFAULT_FILTERS: Filters = {q:'',period:'upcoming',types:[],institution:'',district:'',category:'',scene:'',onlyNew:false,onlySaved:false,onlyFavorites:false,sort:'date',from:'',to:''};
export function filterEvents(events: ArtEvent[], institutions: Institution[], f: Filters, personal: Personal, today=moscowToday()): ArtEvent[] {
  const byId = new Map(institutions.map(i=>[i.institution_id,i]));
  const weekday=(new Date(today+'T12:00:00Z').getUTCDay()+6)%7;
  return events.filter(e=>{
    const i=byId.get(e.institution_id); const last=e.end_date||e.start_date;
    if (!i) return false;
    if(f.q && !normalize([e.title,e.description,i.name,...i.aliases].join(' ')).includes(normalize(f.q))) return false;
    if(f.types.length && !f.types.includes(e.event_type)) return false;
    if(f.institution && f.institution!==e.institution_id) return false;
    if(f.district && !i.districts.includes(f.district)) return false;
    if(f.category && i.entity_type!==f.category)return false;
    if(f.scene==='independent' && !i.independent) return false;
    if(f.scene==='institution' && i.entity_type!=='institution') return false;
    if(f.onlyNew && (!e.first_detected_at || e.first_detected_at<=personal.previousVisit)) return false;
    if(f.onlySaved && !personal.saved.includes(e.event_id)) return false;
    if(f.onlyFavorites && !personal.favorites.includes(e.institution_id)) return false;
    if(f.from && last<f.from) return false;
    if(f.to && e.start_date>f.to) return false;
    if(f.period==='today' && !(e.start_date<=today && last>=today)) return false;
    if(f.period==='tomorrow' && !(e.start_date<=plusDays(today,1) && last>=plusDays(today,1))) return false;
    if(f.period==='week' && (e.start_date>plusDays(today,6-weekday) || last<today)) return false;
    if(f.period==='upcoming' && last<today) return false;
    if(f.period==='ongoing' && !isOngoing(e,today)) return false;
    if(f.period==='archive' && last>=today) return false;
    return true;
  }).sort((a,b)=>f.sort==='new' ? b.first_detected_at.localeCompare(a.first_detected_at) : (a.start_date+(a.start_time||'23:59')).localeCompare(b.start_date+(b.start_time||'23:59')) || a.title.localeCompare(b.title,'ru'));
}
export function filterInstitutions(items: Institution[], f: Filters, personal: Personal) {
  return items.filter(i=>(!f.q||normalize([i.name,...i.aliases,i.focus].join(' ')).includes(normalize(f.q))) && (!f.institution||i.institution_id===f.institution) && (!f.scene||(f.scene==='independent'?i.independent:i.entity_type==='institution')) && (!f.category||i.entity_type===f.category) && (!f.district||i.districts.includes(f.district)) && (!f.onlyFavorites||personal.favorites.includes(i.institution_id)));
}
export function eventICS(e: ArtEvent, institution: Institution) {
  const escape=(s:string)=>s.replaceAll('\r\n','\n').replaceAll('\r','\n').replaceAll('\\','\\\\').replaceAll('\n','\\n').replaceAll(',','\\,').replaceAll(';','\\;');
  const compact=(d:string)=>d.replaceAll('-','');
  const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Moscow Art Monitor//RU','CALSCALE:GREGORIAN','BEGIN:VEVENT',`UID:${escape(e.event_id)}@mscmntr`,`DTSTAMP:${new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'')}`];
  if(e.start_time) {
    const utc=new Date(`${e.start_date}T${e.start_time}:00+03:00`).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
    lines.push(`DTSTART:${utc}`);
    if(e.end_time) lines.push(`DTEND:${new Date(`${e.end_date||e.start_date}T${e.end_time}:00+03:00`).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'')}`);
  } else lines.push(`DTSTART;VALUE=DATE:${compact(e.start_date)}`,`DTEND;VALUE=DATE:${compact(plusDays(e.end_date||e.start_date,1))}`);
  lines.push(`SUMMARY:${escape(e.title)}`,`LOCATION:${escape(e.address||institution.locations[0]?.address||institution.name)}`,`DESCRIPTION:${escape((e.description||'')+'\n'+e.primary_url)}`,`URL:${e.primary_url.replace(/[\r\n]/g,'')}`,'END:VEVENT','END:VCALENDAR');
  // Fold at 75 UTF-8 bytes without splitting Cyrillic codepoints (RFC 5545).
  return lines.map(line=>{let result='',part='';for(const ch of line){if(new TextEncoder().encode(part+ch).length>74){result+=part+'\r\n ';part='';}part+=ch;}return result+part;}).join('\r\n')+'\r\n';
}
export function downloadICS(e: ArtEvent, i: Institution) {
  const url=URL.createObjectURL(new Blob([eventICS(e,i)],{type:'text/calendar;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=`${e.event_id}.ics`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function loadPersonal(): Personal {
  const empty: Personal={favorites:[],saved:[],read:[],previousVisit:new Date().toISOString()};
  try {
    const p=JSON.parse(localStorage.getItem('art-monitor:personal')||'{}');
    for(const key of ['favorites','saved','read'] as const) if(Array.isArray(p[key])) empty[key]=p[key].filter((v:unknown)=>typeof v==='string');
    const previous=localStorage.getItem('art-monitor:last-visit');
    if(previous && !Number.isNaN(Date.parse(previous))) empty.previousVisit=previous;
  } catch { /* A privacy setting can disable storage; session state still works. */ }
  return empty;
}
