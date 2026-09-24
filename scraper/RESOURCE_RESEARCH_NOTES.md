# Research and verification notes

Research date: 24 September 2026.

## Selection method

I prioritized a manageable Python learning sequence, practical code demonstrations, explicit architectural explanations, authoritative robots.txt material, and identifiable legal speakers. I used video descriptions and chapters to assess coverage, rather than rankings based on views or promises to scrape any website.

The outcome is [eight videos in watch order plus one optional legal update](YOUTUBE_LEARNING_PATH.md). Two regional videos are supplements; neither is presented as a full US–China comparison.

## Verification performed

For each of the nine selected videos:

- YouTube's oEmbed endpoint returned its title and channel.
- The public watch page supplied player metadata containing title, runtime, publication date, and description where available.
- The timestamps in the learning guide were taken from the creator's published chapter list, not estimated.

This confirms metadata availability during research. It does **not** confirm playback from every country, guarantee future availability, establish that every spoken claim is correct, or demonstrate compatibility of all tutorial code with current packages. No complete video viewing review or tutorial execution was performed.

| YouTube ID | Channel confirmed | Verification / coverage evidence |
|---|---|---|
| `XVv6mJpFOb0` | freeCodeCamp.org | Watch-page description and chapters: HTML, Beautiful Soup, Requests, saving results. |
| `IXNEVt9rZG8` | Google Search Central | Watch-page chapters and description; technical claims cross-checked with RFC 9309. |
| `oUbXTegNFBs` | Zyte | Watch-page title/date/runtime; description was empty. Scope corroborated using the official conference archive and the speaker's companion article. |
| `mBoX_JCKZTE` | freeCodeCamp.org | Watch-page chapters plus the creator's written course syllabus. |
| `OrMYaPfKDcs` | Oxylabs | Watch-page chapters and description, including dynamic content, export, and commercial access/proxy sections. |
| `krsuaUp__pM` | Hello Interview | Watch-page description and chapters; explicitly an interview-oriented design lesson. |
| `ARGhSwiSWdg` | Cloudflare | Watch-page metadata plus the creator-hosted transcript. |
| `05kNnZty3j8` | Cuatrecasas | Watch-page metadata and law-firm description; explicitly an introduction tied to PIPL's 2021 commencement. |
| `NJ63ygS7LJY` | Extract Summit | Watch-page metadata, official conference archive, and speaker-authored 2025 article. |

Some YouTube pages returned little text or errors through the web-reading tool. Normal public-page and oEmbed retrieval subsequently supplied the metadata above. No login or access-control bypass was used.

## Primary sources supporting the recommendations

- [Scrapy course creator's guide](https://scrapeops.io/python-scrapy-playbook/freecodecamp-beginner-course/) — syllabus and practical-course scope.
- [Scrapy architecture](https://docs.scrapy.org/en/latest/topics/architecture.html) — scheduler, downloader, spider, pipeline, and engine responsibilities.
- [Playwright Python documentation](https://playwright.dev/python/docs/library) — browser automation and current setup reference.
- [Extract Summit official archive](https://www.extractsummit.io/talks) — confirms the 2023 compliance talk and 2025 legal update. Its page data provides their direct YouTube links.
- [Sanaea Daruwalla's 2023 companion article](https://www.scraping.club/p/assessing-legal-compliance-of-web-scraping) — corroborates the review framework; search-index text was available, while direct page retrieval failed.
- [Speaker-authored 2025 legal discussion](https://www.zyte.com/blog/balancing-innovation-and-regulation-in-data-scraping/) — supports the update video's topic. Its broad statements about public data are not adopted as universal legal rules in this guide.
- [Cloudflare's video and transcript](https://developers.cloudflare.com/videos/china-network-inside-china/) — corroborates the short China networking video.
- [Cloudflare China Network overview](https://developers.cloudflare.com/china-network/) — cross-border network context. Vendor material, not a benchmark of your target website.
- [Google: locale-adaptive crawling](https://developers.google.com/search/docs/specialty/international/locale-adaptive-pages) — why visitor geography and language can change the returned content.
- [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html) — normative robots.txt reference.
- [US DOJ Justice Manual: CFAA](https://www.justice.gov/jm/jm-9-48000-computer-fraud) — scope and limitations of federal charging policy.
- [California Attorney General: CCPA](https://oag.ca.gov/privacy/ccpa) — privacy rights and applicability are not determined solely by hosting.
- [US Copyright Office: AI](https://www.copyright.gov/ai/) — official materials on copyright and AI, including training issues; not a blanket approval to train on web content.
- [NPC PIPL, opening articles](https://en.npc.gov.cn.cdurl.cn/2021-12/29/c_694559.htm) and [Articles 27/38](https://en.npc.gov.cn.cdurl.cn/2021-12/29/c_694559_2.htm) — official English publication surfaced by search. Direct web-reader fetches failed; relevant article text was available in search indexing. [NPC bilingual law page](https://www.npc.gov.cn/npc/c2597/c5854/bfflywwb/202311/t20231117_433007.html) is an additional reference.
- [CAC: March 2024 cross-border data provisions](https://www.cac.gov.cn/2024-03/22/c_1712776611775634.htm) — official Chinese text, opened during research. [Hong Kong Digital Policy Office overview](https://www.digitalpolicy.gov.hk/en/our_work/digital_infrastructure/mainland/gbacbdf/) also describes these changes in English.

## Alternatives considered and why the list is limited

- Thomas Janssen's [Playwright Web Scraping Tutorial — Become 100% Undetectable!](https://www.youtube.com/watch?v=afobK3UbTeE): title and channel verified. Not selected because the framing is a poor fit for learning respectful access; no claim of undetectability is endorsed.
- [Zyte's 2023 legal-compliance webinar](https://www.zyte.com/webinars/conducting-a-web-scraping-legal-compliance-review/): relevant speaker and syllabus, but a direct YouTube video was not verified from that landing page. The verified conference talk was chosen instead.
- [Architecting a scalable web scraping project](https://www.youtube.com/watch?v=n-Ar-UQsT3c), Neha Setia Nagpal: found in the official 2022 conference archive. Kept outside the main path to avoid duplicating the Scrapy course and Hello Interview lesson; not subjected to the same individual metadata checks.
- Broad no-code/AI scraper demos and proxy-vendor recommendation lists were not used as the main learning path. They do not replace learning HTTP, parsing, data quality, and source permissions.

## Scope of local changes

This research adds only these three Markdown guides under `scraper/`. The pre-existing `README.md`, scraper modules, and scraped datasets were not modified or audited. Their presence does not verify their accuracy, production readiness, or suitability for a new target site.
