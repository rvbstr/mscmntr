export const CONFIG = {
  title: 'Арт-календарь Москвы',
  repository: 'rvbstr/mscmntr',
  timezone: 'Europe/Moscow',
  workflow: 'https://github.com/rvbstr/mscmntr/actions/workflows/refresh-deploy.yml',
};
export const EVENT_TYPES: Record<string,string> = {opening:'Открытие',exhibition:'Выставка',performance:'Перформанс',talk:'Лекция / дискуссия',screening:'Показ / кино',tour:'Экскурсия',workshop:'Мастер-класс',festival:'Фестиваль / ярмарка',other:'Другое'};
export const STATUS: Record<string,string> = {working:'Работает',partial:'Частично',blocked:'Доступ ограничен',unavailable:'Недоступен',broken:'Ссылка недоступна',review:'Требует проверки',manual:'Ручная проверка',disabled:'Отключён'};
export const PLATFORM: Record<string,string> = {website:'Сайт',telegram:'Телеграм',instagram:'Инстаграм',vk:'ВКонтакте',rss:'RSS / Atom',linkhub:'Ссылки',editorial:'Редакция'};
export const STATES: Record<string,string> = {monitor:'Мониторинг',watchlist:'Наблюдение',excluded:'Исключено из мониторинга',discovery:'Поисковая сеть'};
export const TAGS: Record<string,string> = {artist_run:'Самоорганизация',independent:'Независимое пространство',video:'Видео',sound:'Звук',research:'Исследование',interdisciplinary:'Междисциплинарность',digital:'Цифровое искусство',games:'Игры',archives:'Архивы',art_history:'История искусства',young_art:'Молодое искусство',institutional_critique:'Институциональная критика',nomadic:'Номадический проект',installation:'Инсталляция',material_practices:'Материальные практики',experimental:'Эксперимент',conceptual:'Концептуальное искусство',photography:'Фотография',education:'Образование',international:'Международная программа',residency:'Резиденции',performance:'Перформанс'};

export const CATEGORIES: Record<string,string>={institution:'Институции / музеи',independent_space:'Независимые пространства',cluster:'Арт-кластеры',gallery:'Галереи',education:'Образовательные проекты',review_candidate:'Кандидаты на проверку',artist_run:'Самоорганизации',discovery_network:'Поисковые сети',nomadic_program:'Номадические программы'};
