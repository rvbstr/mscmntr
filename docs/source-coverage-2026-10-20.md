# Аудит источников и площадок · 20 октября 2026

Проверены **189 источников и 92 площадки**. Время завершения: 2026-10-20T18:27:10+00:00.

Все URL каталога; до 6 дочерних страниц сайта на глубину 2, все текущие ссылки публичного API ММОМА (до 40), до 2 страниц Telegram. Архивы сайтов старше 90 дней не добавляются как новые события. Найденные кандидаты не означают подтверждённую московскую площадку.

Это аудит извлечения, а не гарантия полноты афиши. Повторный разбор использует реальные сетевые ответы этого аудита; время загрузки документа хранится отдельно от времени разбора в CSV/JSON. Ноль кандидатов означает, что парсер не распознал анонс; это не доказательство отсутствия программы. Кандидаты иностранных, архивных и агрегаторских страниц не считаются подтверждением московского события. Настройки исключённых площадок и проверки принадлежности сохраняются.

## Методы

- JSON-LD, Microdata/RDFa (Extruct), RSS/Atom; специализированные адаптеры институций.
- ChompJS: безопасный разбор Nuxt и JavaScript-литералов без исполнения кода; JSON встроенных календарей.
- Trafilatura и Beautiful Soup: нестандартные заголовки, компактные даты, карточки программ, двухзначные годы.
- Публичный API ММОМА: календарь выставок и событий, затем страницы отдельных программ и расписания сеансов.
- Chromium/Playwright: выполнение JavaScript после неудачного чтения HTML и состояния страницы.
- Telegram: две страницы публичной ленты, до 40 текстовых постов; API Telethon остаётся опцией.

Публичные страницы читаются в режиме `ROBOTS_POLICY=public`: robots.txt фиксируется в журнале, но его исключения не прекращают чтение. Сохраняются интервалы запросов, TLS и реальные HTTP-ошибки. `ROBOTS_POLICY=respect` включает прежнее поведение. Instagram без настроенного API остаётся ручным источником.

## Результаты чтения

| Результат | Источников |
|---|---:|
| Ограничен доступ | 2 |
| Есть кандидаты | 97 |
| Нужен API / экспорт | 6 |
| Анонсы не распознаны | 78 |
| Прочитано частично | 1 |
| Нужна проверка | 1 |
| Нет соединения | 4 |

## Все площадки

«Кандидаты» — число собственных источников с извлечёнными данными; «Афиша» — реально опубликованные события, включая сохранённые предыдущими сборами.

| Площадка | Источников | Прочитано | Кандидаты | Афиша | Сейчас / впереди |
|---|---:|---:|---:|---:|---:|
| Дом культуры «ГЭС-2» / V–A–C (`MSK001`) | 3 | 3 | 3 | 192 | 108 |
| Музей «Гараж» / Garage Digital (`MSK002`) | 4 | 4 | 3 | 46 | 26 |
| ММОМА (`MSK003`) | 2 | 2 | 2 | 50 | 31 |
| Мультимедиа Арт Музей, Москва / МАММ (`MSK004`) | 3 | 3 | 3 | 11 | 6 |
| Пушкинский музей — медиаискусство и современная программа (`MSK005`) | 3 | 3 | 1 | 8 | 7 |
| Новая Третьяковка / Третьяковская галерея (`MSK006`) | 2 | 2 | 2 | 17 | 13 |
| Музей Москвы (`MSK007`) | 2 | 1 | 1 | 8 | 3 |
| Центр «Зотов» (`MSK008`) | 2 | 2 | 2 | 22 | 14 |
| Фонд Ruarts (`MSK009`) | 2 | 2 | 2 | 26 | 7 |
| ART4 (`MSK010`) | 2 | 2 | 0 | 0 | 0 |
| ЦСИ AZART / AZ/ART (`MSK011`) | 2 | 2 | 2 | 4 | 2 |
| Музей «ЗИЛАРТ» (`MSK012`) | 1 | 0 | 0 | 0 | 0 |
| Фонд культуры «Екатерина» (`MSK013`) | 3 | 3 | 1 | 6 | 0 |
| Stella Art Foundation (`MSK014`) | 1 | 1 | 1 | 4 | 1 |
| In artibus (`MSK015`) | 2 | 2 | 2 | 8 | 3 |
| Государственный Дарвиновский музей — современные проекты (`MSK016`) | 2 | 2 | 1 | 2 | 2 |
| Центр Вознесенского (`MSK017`) | 3 | 3 | 3 | 12 | 7 |
| Зверевский центр свободного искусства (`MSK018`) | 1 | 1 | 0 | 0 | 0 |
| ЦТИ «Фабрика» (`MSK019`) | 2 | 2 | 1 | 4 | 2 |
| ЦСИ «Винзавод» (`MSK020`) | 3 | 3 | 1 | 2 | 0 |
| КУБ / Cube.Moscow (`MSK021`) | 3 | 3 | 2 | 10 | 8 |
| Галерея Солянка (`MSK022`) | 3 | 3 | 1 | 9 | 4 |
| Галерея Ходынка (`MSK023`) | 2 | 2 | 1 | 13 | 2 |
| Галерея Ростокино (`MSK024`) | 3 | 3 | 1 | 15 | 2 |
| Галерея Пересветов переулок (`MSK025`) | 3 | 3 | 1 | 7 | 1 |
| Краснохолмская + SA))_gallery / SoundArtist.ru (`MSK026`) | 3 | 3 | 1 | 3 | 0 |
| Галерея на Шаболовке (`MSK027`) | 2 | 2 | 1 | 5 | 1 |
| Галерея Беляево (`MSK028`) | 1 | 1 | 0 | 0 | 0 |
| Школа Родченко (`MSK029`) | 3 | 3 | 1 | 3 | 1 |
| HSE ART GALLERY / Галерея Школы дизайна НИУ ВШЭ (`MSK030`) | 4 | 4 | 4 | 7 | 4 |
| Галерея MSCA (`MSK031`) | 2 | 2 | 2 | 4 | 3 |
| U Contemporary / Universal University (`MSK032`) | 2 | 2 | 2 | 0 | 0 |
| Триумф / Triumph (`MSK033`) | 2 | 2 | 2 | 9 | 6 |
| XL (`MSK034`) | 1 | 1 | 1 | 6 | 2 |
| OVCHARENKO (`MSK035`) | 1 | 1 | 1 | 14 | 0 |
| pop/off/art + pop/off/art 2.0 (`MSK036`) | 2 | 2 | 2 | 8 | 4 |
| Сцена / Szena (`MSK037`) | 4 | 2 | 1 | 1 | 0 |
| а—с—т—р—а / a-s-t-r-a (`MSK038`) | 3 | 3 | 1 | 3 | 2 |
| PENNLAB (`MSK039`) | 3 | 3 | 2 | 7 | 2 |
| fābula gallery / fābula HQ (`MSK040`) | 3 | 3 | 0 | 0 | 0 |
| VS Gallery (`MSK041`) | 2 | 2 | 1 | 5 | 5 |
| Generative Gallery (`MSK042`) | 3 | 3 | 1 | 7 | 5 |
| ПиранезиLAB (`MSK043`) | 4 | 4 | 3 | 17 | 5 |
| Крокин галерея (`MSK044`) | 2 | 2 | 0 | 0 | 0 |
| Reloft ART (`MSK045`) | 2 | 2 | 0 | 0 | 0 |
| БУДУЩЕЕ / FUTURO — московская площадка (`MSK046`) | 3 | 3 | 1 | 7 | 3 |
| Syntax (`MSK047`) | 2 | 2 | 0 | 0 | 0 |
| PA Gallery (`MSK048`) | 1 | 1 | 0 | 0 | 0 |
| LUCH (`MSK049`) | 1 | 1 | 0 | 0 | 0 |
| КультПроект (`MSK050`) | 2 | 1 | 0 | 0 | 0 |
| 11.12 Gallery (`MSK051`) | 2 | 2 | 1 | 2 | 2 |
| Файн Арт / Fine Art (`MSK052`) | 3 | 3 | 1 | 5 | 1 |
| Галерея Тотибадзе (`MSK053`) | 2 | 2 | 0 | 0 | 0 |
| ARTSTORY (`MSK054`) | 1 | 1 | 0 | 0 | 0 |
| Галерея Погодиной / Pogodina gallery (`MSK055`) | 2 | 2 | 0 | 0 | 0 |
| ART & BRUT (`MSK056`) | 1 | 0 | 0 | 0 | 0 |
| Галерея Люмьер / Lumiere (`MSK057`) | 3 | 3 | 2 | 2 | 1 |
| Центр визуальной культуры Béton (`MSK058`) | 2 | 2 | 1 | 2 | 1 |
| Atelier CHOUTKO / Галерея Евгения Шутко (`MSK059`) | 1 | 0 | 0 | 0 | 0 |
| Галерея Ruarts — завершающая программа (`MSK060`) | 1 | 1 | 1 | 4 | 2 |
| Мастерская Арендт&Co (`MSK061`) | 1 | 1 | 1 | 10 | 0 |
| ЗАЙКА Space (`MSK062`) | 1 | 1 | 1 | 3 | 0 |
| murmure (`MSK063`) | 2 | 2 | 1 | 1 | 1 |
| Галерея «Бомба» (`MSK064`) | 2 | 2 | 1 | 3 | 1 |
| Текстура / TEXTURA Gallery (`MSK065`) | 3 | 3 | 3 | 8 | 3 |
| SAMPLE (`MSK066`) | 2 | 2 | 1 | 2 | 2 |
| Artwin — московская программа (`MSK067`) | 2 | 2 | 0 | 6 | 0 |
| Madame / madame_space (`WATCH01`) | 2 | 1 | 0 | 0 | 0 |
| Галерея «Корней» (`WATCH03`) | 4 | 4 | 0 | 0 | 0 |
| ±space / plus-minus space (`WATCH04`) | 1 | 1 | 0 | 0 | 0 |
| Пространство пространств (`WATCH05`) | 5 | 4 | 3 | 10 | 4 |
| NoNameForNow / NNFN (`WATCH06`) | 4 | 4 | 0 | 0 | 0 |
| Институт «БАЗА» (`WATCH07`) | 2 | 2 | 1 | 0 | 0 |
| IRAGUI (`WATCH08`) | 2 | 2 | 2 | 3 | 1 |
| Галерея «Электрозавод» / старый кластер (`WATCH09`) | 2 | 2 | 0 | 0 | 0 |
| Электромузей (`WATCH10`) | 2 | 2 | 0 | 0 | 0 |
| Fragment Gallery (`WATCH11`) | 1 | 1 | 0 | 0 | 0 |
| ALISA Gallery (`WATCH12`) | 1 | 1 | 0 | 0 | 0 |
| Lazy Mike — старое московское пространство (`WATCH13`) | 1 | 1 | 0 | 0 | 0 |
| Галерея 9Б (`WATCH14`) | 1 | 1 | 0 | 0 | 0 |
| aroundart.org (`WATCH15`) | 1 | 0 | 0 | 0 | 0 |
| Ассоциация галерей / АГА (`NET01`) | 1 | 1 | 0 | 0 | 0 |
| Эверт (`NET04`) | 1 | 1 | 0 | 0 | 0 |
| Проcтранство / prstrnst (`NET05`) | 1 | 1 | 1 | 0 | 0 |
| Cosmoscow (`NET06`) | 2 | 2 | 2 | 0 | 0 |
| blazar (`NET07`) | 2 | 2 | 1 | 0 | 0 |
| «Куча» — сеть самоорганизаций (`NET08`) | 1 | 1 | 0 | 0 | 0 |
| АРТ МОСКВА (`NET09`) | 2 | 2 | 1 | 0 | 0 |
| Иваний галерея / IVANY GALLERY (`MSK068`) | 2 | 2 | 1 | 5 | 3 |
| Девятнадцать / Devyatnadtsat’ Gallery (`MSK069`) | 6 | 5 | 2 | 14 | 1 |
| ДНИ / дом независимого искусства (`MSK070`) | 4 | 2 | 2 | 7 | 4 |
| VIDEO VIOLENCE / Spas Setun (`MSK071`) | 4 | 3 | 0 | 0 | 0 |

## Все источники

Полные ошибки и страницы: [JSON](../public/data/coverage.json). Таблица для проверки и фильтрации: [CSV](../public/data/coverage.csv).

| Источник | Результат | Парсер | Кандидатов |
|---|---|---|---:|
| [https://t.me/video_violence](https://t.me/video_violence) | Анонсы не распознаны | telegram_public_preview | 0 |
| [https://rostokino.vzmoscow.ru/contacts](https://rostokino.vzmoscow.ru/contacts) | Анонсы не распознаны | — | 0 |
| [https://gallery.reloft.art/](https://gallery.reloft.art/) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://artandbrutgallery.com/](https://artandbrutgallery.com/) | Нет соединения | — | 0 |
| [https://t.me/rostokino_gallery](https://t.me/rostokino_gallery) | Есть кандидаты | telegram_public_preview | 15 |
| [https://t.me/devyatnadtsat](https://t.me/devyatnadtsat) | Есть кандидаты | telegram_public_preview | 9 |
| [https://www.krokingallery.com/](https://www.krokingallery.com/) | Анонсы не распознаны | — | 0 |
| [https://lumiere.ru/art-fairs/cosmoscow-2026/](https://lumiere.ru/art-fairs/cosmoscow-2026/) | Есть кандидаты | extruct_trafilatura, jsonld | 4 |
| [https://piranesilab.ru/contacts/](https://piranesilab.ru/contacts/) | Есть кандидаты | extruct_trafilatura, programme_cards | 11 |
| [https://russianartarchive.net/ru/catalogue/organization/OYSF](https://russianartarchive.net/ru/catalogue/organization/OYSF) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://www.piranesilab.ru/](https://www.piranesilab.ru/) | Есть кандидаты | extruct_trafilatura, programme_cards | 2 |
| [https://ewert.ru/exhibitions/zti-fabrika/](https://ewert.ru/exhibitions/zti-fabrika/) | Есть кандидаты | jsonld | 14 |
| [https://a-s-t-r-a.ru/](https://a-s-t-r-a.ru/) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://t.me/texturagallery](https://t.me/texturagallery) | Есть кандидаты | telegram_public_preview | 5 |
| [https://t.me/pop_off_art](https://t.me/pop_off_art) | Есть кандидаты | telegram_public_preview | 8 |
| [https://www.darwinmuseum.ru/projects/exhibition/stihijnost-prostranstvo-dvizhenie-zvuk](https://www.darwinmuseum.ru/projects/exhibition/stihijnost-prostranstvo-dvizhenie-zvuk) | Есть кандидаты | extruct_trafilatura | 2 |
| [https://mamm-mdf.ru/](https://mamm-mdf.ru/) | Есть кандидаты | extruct_trafilatura | 6 |
| [https://t.me/murmurespace](https://t.me/murmurespace) | Есть кандидаты | telegram_public_preview | 1 |
| [https://zilartmuseum.ru/exhibitions/ma-prostranstvo-mezhdu/](https://zilartmuseum.ru/exhibitions/ma-prostranstvo-mezhdu/) | Ограничен доступ | — | 0 |
| [https://t.me/piranesilab](https://t.me/piranesilab) | Есть кандидаты | telegram_public_preview | 7 |
| [https://www.winzavod.ru/residents/](https://www.winzavod.ru/residents/) | Анонсы не распознаны | — | 0 |
| [https://aroundart.org/](https://aroundart.org/) | Нужна проверка | — | 0 |
| [https://t.me/statedarwinmuseum](https://t.me/statedarwinmuseum) | Анонсы не распознаны | telegram_public_preview | 0 |
| [https://alisagallery.art/ru](https://alisagallery.art/ru) | Анонсы не распознаны | programme_cards | 0 |
| [https://t.me/voznesenskycenter](https://t.me/voznesenskycenter) | Есть кандидаты | telegram_public_preview | 8 |
| [https://ges-2.org/](https://ges-2.org/) | Есть кандидаты | extruct_trafilatura | 3 |
| [https://garage.digital/ru/](https://garage.digital/ru/) | Анонсы не распознаны | — | 0 |
| [https://spassetun.org/](https://spassetun.org/) | Анонсы не распознаны | — | 0 |
| [https://t.me/hsedesign](https://t.me/hsedesign) | Есть кандидаты | telegram_public_preview | 1 |
| [https://t.me/dniculture](https://t.me/dniculture) | Есть кандидаты | telegram_public_preview | 7 |
| [https://www.instagram.com/prostranstvo.prostranstv/](https://www.instagram.com/prostranstvo.prostranstv/) | Нужен API / экспорт | — | 0 |
| [https://t.me/hseartgallery](https://t.me/hseartgallery) | Есть кандидаты | telegram_public_preview | 4 |
| [https://agarussia.art/afisha](https://agarussia.art/afisha) | Анонсы не распознаны | — | 0 |
| [https://t.me/prostranstvoprostranstv](https://t.me/prostranstvoprostranstv) | Есть кандидаты | telegram_public_preview | 5 |
| [https://pennlab.shop/](https://pennlab.shop/) | Есть кандидаты | extruct_trafilatura, programme_cards | 2 |
| [https://t.me/gt_gallery](https://t.me/gt_gallery) | Есть кандидаты | telegram_public_preview | 6 |
| [https://t.me/mmoma](https://t.me/mmoma) | Есть кандидаты | telegram_public_preview | 9 |
| [https://inartibus.org/](https://inartibus.org/) | Есть кандидаты | programme_cards | 3 |
| [https://ivanygallery.com/](https://ivanygallery.com/) | Анонсы не распознаны | — | 0 |
| [https://www.theartnewspaper.ru/posts/20260623-ihpf/](https://www.theartnewspaper.ru/posts/20260623-ihpf/) | Анонсы не распознаны | — | 0 |
| [https://cube.moscow/galleries/](https://cube.moscow/galleries/) | Анонсы не распознаны | — | 0 |
| [https://fragment.gallery/exhibitions/](https://fragment.gallery/exhibitions/) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://t.me/museumart4](https://t.me/museumart4) | Анонсы не распознаны | telegram_public_preview | 0 |
| [https://prpr312.ru/](https://prpr312.ru/) | Есть кандидаты | extruct_trafilatura, institution | 6 |
| [https://ruarts.foundation/ru/](https://ruarts.foundation/ru/) | Есть кандидаты | extruct_trafilatura, institution | 12 |
| [https://11-12gallery.com/](https://11-12gallery.com/) | Есть кандидаты | institution | 2 |
| [https://pushkinmuseum.art/events/archive/2026/exhibitions/fabrizio_plessi_vertical_seas/index.php?lang=it](https://pushkinmuseum.art/events/archive/2026/exhibitions/fabrizio_plessi_vertical_seas/index.php?lang=it) | Анонсы не распознаны | — | 0 |
| [https://www.galleryfineart.ru/](https://www.galleryfineart.ru/) | Анонсы не распознаны | — | 0 |
| [https://ovcharenko.art/](https://ovcharenko.art/) | Есть кандидаты | extruct_trafilatura | 2 |
| [https://mdfschool.ru/events/all/diplom_2026/](https://mdfschool.ru/events/all/diplom_2026/) | Анонсы не распознаны | — | 0 |
| [https://mamm.art/](https://mamm.art/) | Есть кандидаты | extruct_trafilatura | 6 |
| [https://t.me/aacademy19](https://t.me/aacademy19) | Есть кандидаты | telegram_public_preview | 4 |
| [https://garagemca.org/](https://garagemca.org/) | Есть кандидаты | institution | 21 |
| [https://www.tretyakovgallery.ru/for-visitors/museums/novaya-tretyakovka/](https://www.tretyakovgallery.ru/for-visitors/museums/novaya-tretyakovka/) | Есть кандидаты | embedded_calendar | 12 |
| [https://t.me/againstthedigital](https://t.me/againstthedigital) | Есть кандидаты | telegram_public_preview | 3 |
| [https://t.me/na_shabolovke](https://t.me/na_shabolovke) | Есть кандидаты | telegram_public_preview | 7 |
| [https://bazaeducation.ru/](https://bazaeducation.ru/) | Анонсы не распознаны | — | 0 |
| [https://t.me/betoncvc](https://t.me/betoncvc) | Анонсы не распознаны | telegram_public_preview | 0 |
| [https://t.me/solyankagallery](https://t.me/solyankagallery) | Есть кандидаты | telegram_public_preview | 18 |
| [https://www.art-story.com/](https://www.art-story.com/) | Анонсы не распознаны | — | 0 |
| [https://ewert.ru/institutions/galereya-kornej/](https://ewert.ru/institutions/galereya-kornej/) | Анонсы не распознаны | jsonld | 0 |
| [https://www.instagram.com/szenamoscow/](https://www.instagram.com/szenamoscow/) | Нужен API / экспорт | — | 0 |
| [https://fabrikacci.com/events.html](https://fabrikacci.com/events.html) | Анонсы не распознаны | — | 0 |
| [https://solyanka.vzmoscow.ru/exhibitions](https://solyanka.vzmoscow.ru/exhibitions) | Анонсы не распознаны | — | 0 |
| [https://szena-gallery.com/](https://szena-gallery.com/) | Анонсы не распознаны | — | 0 |
| [https://tg.me/dniculture](https://tg.me/dniculture) | Есть кандидаты | telegram_public_preview | 7 |
| [https://murmure.space/](https://murmure.space/) | Анонсы не распознаны | — | 0 |
| [https://texturagallery.com/event43](https://texturagallery.com/event43) | Есть кандидаты | extruct_trafilatura | 4 |
| [https://t.me/bazaeducation](https://t.me/bazaeducation) | Есть кандидаты | telegram_public_preview | 1 |
| [https://t.me/ruartsfoundation](https://t.me/ruartsfoundation) | Есть кандидаты | telegram_public_preview | 12 |
| [https://spassetun.org/exhibitions/let-me-become-a-hundred-yetti](https://spassetun.org/exhibitions/let-me-become-a-hundred-yetti) | Анонсы не распознаны | — | 0 |
| [https://t.me/krokingallery](https://t.me/krokingallery) | Анонсы не распознаны | telegram_public_preview | 0 |
| [https://artandyou.ru/interview/art-professionals/osnovateli-yarmarki-hudozhestvennyh-samoorganizaczij-kucha-kak-nezavisimoe-iskusstvo-obzhivaet-novye-formaty/](https://artandyou.ru/interview/art-professionals/osnovateli-yarmarki-hudozhestvennyh-samoorganizaczij-kucha-kak-nezavisimoe-iskusstvo-obzhivaet-novye-formaty/) | Анонсы не распознаны | — | 0 |
| [https://zverevcenter.ru/](https://zverevcenter.ru/) | Анонсы не распознаны | — | 0 |
| [https://ruarts.gallery/](https://ruarts.gallery/) | Есть кандидаты | extruct_trafilatura | 2 |
| [https://russianartarchive.net/ru/catalogue/event/ECWTF](https://russianartarchive.net/ru/catalogue/event/ECWTF) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://t.me/prstrnst](https://t.me/prstrnst) | Есть кандидаты | telegram_public_preview | 3 |
| [https://art.hse.ru/gallery/we_choose_we_are_chosen](https://art.hse.ru/gallery/we_choose_we_are_chosen) | Есть кандидаты | institution | 1 |
| [https://linktr.ee/piranesilab](https://linktr.ee/piranesilab) | Анонсы не распознаны | — | 0 |
| [https://agarussia.art/players](https://agarussia.art/players) | Анонсы не распознаны | — | 0 |
| [https://www.cosmoscow.com/ru/](https://www.cosmoscow.com/ru/) | Есть кандидаты | extruct_trafilatura, programme_cards | 6 |
| [https://vs.gallery/](https://vs.gallery/) | Анонсы не распознаны | — | 0 |
| [https://t.me/cube_moscow](https://t.me/cube_moscow) | Есть кандидаты | telegram_public_preview | 5 |
| [https://t.me/vsgall](https://t.me/vsgall) | Есть кандидаты | telegram_public_preview | 14 |
| [https://blazar.art/](https://blazar.art/) | Анонсы не распознаны | — | 0 |
| [https://ekaterina-foundation.ru/rus/](https://ekaterina-foundation.ru/rus/) | Анонсы не распознаны | — | 0 |
| [https://soundartist.ru/gallery/](https://soundartist.ru/gallery/) | Анонсы не распознаны | — | 0 |
| [https://t.me/multimediaartmuseum](https://t.me/multimediaartmuseum) | Есть кандидаты | telegram_public_preview | 5 |
| [https://spassetun.org/about](https://spassetun.org/about) | Анонсы не распознаны | — | 0 |
| [https://www.generativegallery.com/about/](https://www.generativegallery.com/about/) | Анонсы не распознаны | — | 0 |
| [https://t.me/arendt_and_co](https://t.me/arendt_and_co) | Есть кандидаты | telegram_public_preview | 10 |
| [https://soundartist.ru/gallery/about/](https://soundartist.ru/gallery/about/) | Анонсы не распознаны | — | 0 |
| [https://t.me/vacges2](https://t.me/vacges2) | Есть кандидаты | telegram_public_preview | 6 |
| [https://ewert.ru/exhibitions/](https://ewert.ru/exhibitions/) | Есть кандидаты | jsonld | 12 |
| [https://msca.ru/galleries](https://msca.ru/galleries) | Есть кандидаты | extruct_trafilatura | 2 |
| [https://mmoma.ru/visit/events](https://mmoma.ru/visit/events) | Есть кандидаты | extruct_trafilatura, institution, mmoma_public_api | 42 |
| [https://www.cosmoscow.com/ru/galleries/2026/gallery-837/](https://www.cosmoscow.com/ru/galleries/2026/gallery-837/) | Анонсы не распознаны | — | 0 |
| [https://art.hse.ru/gallery](https://art.hse.ru/gallery) | Есть кандидаты | institution | 4 |
| [https://t.me/galleryfineart](https://t.me/galleryfineart) | Есть кандидаты | telegram_public_preview | 5 |
| [https://mdfschool.ru/events/](https://mdfschool.ru/events/) | Анонсы не распознаны | — | 0 |
| [https://www.instagram.com/19_devyatnadtsat/](https://www.instagram.com/19_devyatnadtsat/) | Нужен API / экспорт | — | 0 |
| [https://syntaxgallery.com/](https://syntaxgallery.com/) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://t.me/cci_fabrika](https://t.me/cci_fabrika) | Есть кандидаты | telegram_public_preview | 3 |
| [https://www.winzavod.ru/](https://www.winzavod.ru/) | Анонсы не распознаны | — | 0 |
| [https://t.me/centrezotov](https://t.me/centrezotov) | Есть кандидаты | telegram_public_preview | 9 |
| [https://artwingallery.com/](https://artwingallery.com/) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://t.me/blazarart](https://t.me/blazarart) | Есть кандидаты | telegram_public_preview | 3 |
| [https://www.instagram.com/dni.culture/](https://www.instagram.com/dni.culture/) | Нужен API / экспорт | — | 0 |
| [https://t.me/mosmuseum](https://t.me/mosmuseum) | Есть кандидаты | telegram_public_preview | 8 |
| [https://fabrikacci.com/residents/galereya-bomba.html](https://fabrikacci.com/residents/galereya-bomba.html) | Анонсы не распознаны | — | 0 |
| [https://t.me/galereyabomba](https://t.me/galereyabomba) | Есть кандидаты | telegram_public_preview | 3 |
| [https://t.me/artmoscowfair](https://t.me/artmoscowfair) | Есть кандидаты | telegram_public_preview | 2 |
| [https://t.me/iragui](https://t.me/iragui) | Есть кандидаты | telegram_public_preview | 1 |
| [https://www.safmuseum.org/](https://www.safmuseum.org/) | Есть кандидаты | extruct_trafilatura | 2 |
| [https://rostokino.vzmoscow.ru/about](https://rostokino.vzmoscow.ru/about) | Анонсы не распознаны | — | 0 |
| [https://futurogallery.ru/](https://futurogallery.ru/) | Анонсы не распознаны | — | 0 |
| [https://belyaevo.vzmoscow.ru/](https://belyaevo.vzmoscow.ru/) | Анонсы не распознаны | — | 0 |
| [https://mdfschool.ru/events/all/news_url_perspectiva_slozhnosti_26/](https://mdfschool.ru/events/all/news_url_perspectiva_slozhnosti_26/) | Анонсы не распознаны | — | 0 |
| [https://sample-art.com/events/exhibitions](https://sample-art.com/events/exhibitions) | Анонсы не распознаны | — | 0 |
| [https://t.me/fabula_gallery](https://t.me/fabula_gallery) | Анонсы не распознаны | telegram_public_preview | 0 |
| [https://prpr312.ru/zhivopis-for-anya](https://prpr312.ru/zhivopis-for-anya) | Есть кандидаты | extruct_trafilatura, institution | 6 |
| [https://centrezotov.ru/](https://centrezotov.ru/) | Есть кандидаты | institution | 10 |
| [https://www.iragui.com/](https://www.iragui.com/) | Есть кандидаты | embedded_calendar, programme_cards | 4 |
| [https://khodynka.vzmoscow.ru/](https://khodynka.vzmoscow.ru/) | Анонсы не распознаны | — | 0 |
| [https://www.triumph.gallery/](https://www.triumph.gallery/) | Есть кандидаты | extruct_trafilatura, programme_cards | 4 |
| [https://totibadzegallery.ru/](https://totibadzegallery.ru/) | Анонсы не распознаны | — | 0 |
| [https://t.me/cca_winzavod](https://t.me/cca_winzavod) | Есть кандидаты | telegram_public_preview | 2 |
| [https://t.me/ivanygallery](https://t.me/ivanygallery) | Есть кандидаты | telegram_public_preview | 6 |
| [https://peresvetov.vzmoscow.ru/original](https://peresvetov.vzmoscow.ru/original) | Анонсы не распознаны | — | 0 |
| [https://texturagallery.com/events](https://texturagallery.com/events) | Есть кандидаты | extruct_trafilatura | 3 |
| [https://www.instagram.com/madame_space/](https://www.instagram.com/madame_space/) | Нужен API / экспорт | — | 0 |
| [https://t.me/theartsmuseum](https://t.me/theartsmuseum) | Есть кандидаты | telegram_public_preview | 8 |
| [https://t.me/khodynkagallery](https://t.me/khodynkagallery) | Есть кандидаты | telegram_public_preview | 13 |
| [https://t.me/uumsca](https://t.me/uumsca) | Есть кандидаты | telegram_public_preview | 2 |
| [https://devyatnadtsat.com/about](https://devyatnadtsat.com/about) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://nonamefornow.tilda.ws/](https://nonamefornow.tilda.ws/) | Анонсы не распознаны | extruct_trafilatura, programme_cards | 0 |
| [https://art-moscow.ru/](https://art-moscow.ru/) | Анонсы не распознаны | — | 0 |
| [https://azart.moscow/](https://azart.moscow/) | Есть кандидаты | extruct_trafilatura | 2 |
| [https://fabrikacci.com/](https://fabrikacci.com/) | Анонсы не распознаны | — | 0 |
| [https://design.hse.ru/news/5694](https://design.hse.ru/news/5694) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://ewert.ru/exhibition/bukety-i-zakaty/](https://ewert.ru/exhibition/bukety-i-zakaty/) | Есть кандидаты | jsonld | 1 |
| [https://t.me/szena](https://t.me/szena) | Прочитано частично | — | 0 |
| [https://t.me/pennlab](https://t.me/pennlab) | Есть кандидаты | telegram_public_preview | 7 |
| [https://www.popoffart.com/](https://www.popoffart.com/) | Есть кандидаты | extruct_trafilatura, programme_cards | 1 |
| [https://www.generativegallery.com/](https://www.generativegallery.com/) | Анонсы не распознаны | — | 0 |
| [https://t.me/lumiere_gallery](https://t.me/lumiere_gallery) | Анонсы не распознаны | telegram_public_preview | 0 |
| [https://t.me/astraartgallery](https://t.me/astraartgallery) | Есть кандидаты | telegram_public_preview | 3 |
| [https://t.me/garagemca](https://t.me/garagemca) | Есть кандидаты | telegram_public_preview | 4 |
| [https://gallery.reloft.art/events/2026/](https://gallery.reloft.art/events/2026/) | Анонсы не распознаны | — | 0 |
| [https://t.me/azart_moscow](https://t.me/azart_moscow) | Есть кандидаты | telegram_public_preview | 2 |
| [https://shabolovka.vzmoscow.ru/](https://shabolovka.vzmoscow.ru/) | Анонсы не распознаны | — | 0 |
| [https://fabulagallery.com/ru/programme/](https://fabulagallery.com/ru/programme/) | Анонсы не распознаны | — | 0 |
| [https://t.me/triumphgallery](https://t.me/triumphgallery) | Есть кандидаты | telegram_public_preview | 8 |
| [https://xl.gallery/](https://xl.gallery/) | Есть кандидаты | extruct_trafilatura | 5 |
| [https://peresvetov.vzmoscow.ru/](https://peresvetov.vzmoscow.ru/) | Анонсы не распознаны | — | 0 |
| [https://t.me/rodchenkoartschool](https://t.me/rodchenkoartschool) | Есть кандидаты | telegram_public_preview | 3 |
| [https://ewert.ru/institutions/plus-minus-space/](https://ewert.ru/institutions/plus-minus-space/) | Есть кандидаты | jsonld | 14 |
| [https://www.afisha.ru/msk/gallery/lazy-mike-23328/](https://www.afisha.ru/msk/gallery/lazy-mike-23328/) | Есть кандидаты | jsonld | 129 |
| [https://kultproekt.ru/](https://kultproekt.ru/) | Нет соединения | — | 0 |
| [https://meduza.io/feature/2026/09/08/v-moskve-snosyat-elektrozavod-fasady-obeschayut-sohranit-no-net-garantiy-chto-ih-ne-zamenyat-novodelom](https://meduza.io/feature/2026/09/08/v-moskve-snosyat-elektrozavod-fasady-obeschayut-sohranit-no-net-garantiy-chto-ih-ne-zamenyat-novodelom) | Анонсы не распознаны | — | 0 |
| [https://mosmuseum.ru/events/](https://mosmuseum.ru/events/) | Ограничен доступ | — | 0 |
| [https://t.me/ekaterinafoundation](https://t.me/ekaterinafoundation) | Есть кандидаты | telegram_public_preview | 6 |
| [https://pushkinmuseum.art/events/](https://pushkinmuseum.art/events/) | Анонсы не распознаны | — | 0 |
| [https://art4.ru/](https://art4.ru/) | Анонсы не распознаны | — | 0 |
| [https://t.me/futuro_gallery](https://t.me/futuro_gallery) | Есть кандидаты | telegram_public_preview | 7 |
| [https://artwingallery.com/contact/](https://artwingallery.com/contact/) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://www.voznesenskycenter.ru/](https://www.voznesenskycenter.ru/) | Есть кандидаты | extruct_trafilatura | 2 |
| [https://t.me/cosmoscowfair](https://t.me/cosmoscowfair) | Есть кандидаты | telegram_public_preview | 3 |
| [https://www.instagram.com/spassetun/](https://www.instagram.com/spassetun/) | Нужен API / экспорт | — | 0 |
| [https://ges-2.org/calendar](https://ges-2.org/calendar) | Есть кандидаты | institution | 58 |
| [https://www.voznesenskycenter.ru/exhibitions/](https://www.voznesenskycenter.ru/exhibitions/) | Есть кандидаты | extruct_trafilatura | 3 |
| [https://glebivany.com/](https://glebivany.com/) | Нет соединения | — | 0 |
| [https://t.me/inartibus](https://t.me/inartibus) | Есть кандидаты | telegram_public_preview | 7 |
| [https://www.choutko.com/](https://www.choutko.com/) | Нет соединения | — | 0 |
| [https://t.me/zaykaspace](https://t.me/zaykaspace) | Есть кандидаты | telegram_public_preview | 3 |
| [https://lumiere.ru/](https://lumiere.ru/) | Есть кандидаты | extruct_trafilatura, jsonld | 2 |
| [https://t.me/soundartist_ru](https://t.me/soundartist_ru) | Есть кандидаты | telegram_public_preview | 3 |
| [https://solyanka.vzmoscow.ru/](https://solyanka.vzmoscow.ru/) | Анонсы не распознаны | — | 0 |
| [https://cube.moscow/exhibitions/](https://cube.moscow/exhibitions/) | Есть кандидаты | institution | 6 |
| [https://betoncvc.com/](https://betoncvc.com/) | Есть кандидаты | extruct_trafilatura | 2 |
| [https://t.me/peresvetovgallery](https://t.me/peresvetovgallery) | Есть кандидаты | telegram_public_preview | 7 |
| [https://aacademy19.com/work1](https://aacademy19.com/work1) | Анонсы не распознаны | — | 0 |
| [https://t.me/szenagallery](https://t.me/szenagallery) | Есть кандидаты | telegram_public_preview | 1 |
| [https://fabulagallery.com/ru/](https://fabulagallery.com/ru/) | Анонсы не распознаны | — | 0 |
| [https://pogodinagallery.com/](https://pogodinagallery.com/) | Анонсы не распознаны | — | 0 |
| [https://devyatnadtsat.com/](https://devyatnadtsat.com/) | Анонсы не распознаны | extruct_trafilatura | 0 |
| [https://t.me/sampleart](https://t.me/sampleart) | Есть кандидаты | telegram_public_preview | 2 |
| [https://t.me/generativegallery](https://t.me/generativegallery) | Есть кандидаты | telegram_public_preview | 7 |
| [https://fabrikacci.com/exhibitions/archive/i-posle-agent-kuper-povtoril-net-takogo-mesta-kak-dom.html](https://fabrikacci.com/exhibitions/archive/i-posle-agent-kuper-povtoril-net-takogo-mesta-kak-dom.html) | Анонсы не распознаны | — | 0 |
