# Web scraping: US versus mainland China

Researched 24 September 2026. This is a beginner's issue map, not a legal determination for a particular dataset.

**Moving a website's server from the US to China does not automatically change the scraping code or settle which laws apply.** Separate five things: website operator, people represented in the data, hosting/CDN location, scraper execution location, and where the collected data will be stored or used. The distinction follows from laws such as PIPL, whose scope concerns processing and people in China, including specified processing outside China—not simply the server's postal address. See [PIPL Article 3](https://en.npc.gov.cn.cdurl.cn/2021-12/29/c_694559.htm).

Here, “China” means **mainland China**. Do not automatically apply this comparison to Hong Kong or Macau.

## The videos to pair

- [Cloudflare: How to speed up your web traffic inside Mainland China](https://www.youtube.com/watch?v=ARGhSwiSWdg) — **2:41**. Network and deployment context; a vendor explainer, not a scraper tutorial.
- [Cuatrecasas: China's Personal Information Protection Law](https://www.youtube.com/watch?v=05kNnZty3j8) — **40:15**. Privacy-law foundations from 2021; not a current cross-border compliance manual.
- [Zyte: A Step By Step Guide To Assessing Your Web Scraping Compliance](https://www.youtube.com/watch?v=oUbXTegNFBs) — **35:44**. General project review process; not a complete China analysis.
- Optional: [Extract Summit: Balancing Innovation and Regulation in Web Scraping](https://www.youtube.com/watch?v=NJ63ygS7LJY) — **24:44**, 2025. Later discussion of scraping and AI legal developments.

I did not find a sufficiently reliable beginner YouTube video that directly covers the full US–China comparison. The table below fills that gap using official sources and explicitly labelled engineering implications.

## What changes in practice?

| Dimension | US-hosted target | Mainland-China-hosted target | Implication for your scraper / ML dataset |
|---|---|---|---|
| HTTP and extraction | May serve HTML, JSON APIs, or JavaScript-rendered pages. | The same general possibilities exist. | Choose Requests/Beautiful Soup, Scrapy, or Playwright from observed page behavior. Country alone does not select the library. |
| Network path | Distance, CDN routing, outages, and site policy affect access. | Cross-border paths can add latency, reliability problems, and filtering. A visitor inside China accessing a US origin is a different path from a visitor outside China accessing a mainland origin. | Engineering implication: measure from the actual authorized execution location; distinguish DNS/connectivity failures from HTTP denials and parsing errors. Avoid multiplying retries indiscriminately. [Cloudflare network documentation](https://developers.cloudflare.com/china-network/) |
| Content shown | A US server can return localized content to visitors elsewhere. | A mainland server can also return different regional/language versions. | IP geography and language preferences can affect the response. Record locale and source region; do not label data as “US data” merely because the server is in the US. [Google's locale-adaptive crawling explanation](https://developers.google.com/search/docs/specialty/international/locale-adaptive-pages) |
| Website controls | Authentication, WAFs, rate limits, CAPTCHAs, and crawler policies are site-specific. | The same categories may exist, with different implementations. | Do not assume “US is easy / China is hard.” Identify the actual restriction, honor it, and use an authorized access route. Robots directives are separate from authentication. [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html) |
| Personal information | Applicable state and sector-specific requirements depend on the activity and entity. California's CCPA has scope rules and exemptions; it is not a universal rule for every US page. | PIPL can apply to processing in China and certain processing outside China involving people there. Publicly disclosed information is not unrestricted: Article 27 places conditions on processing it. | Assess people, purpose, and legal scope, not only the domain suffix or host IP. Prefer nonpersonal data for your first exercise. [California AG](https://oag.ca.gov/privacy/ccpa), [PIPL Arts. 3 and 27](https://en.npc.gov.cn.cdurl.cn/2021-12/29/c_694559_2.htm) |
| Access and reuse | Computer-access law, contract terms, copyright, and privacy are distinct questions. | PIPL and data-security requirements add questions alongside access, contracts, and intellectual property. | “The page is public” and “the HTTP request worked” do not resolve all these questions. ML training is an intended use to assess separately. [DOJ CFAA policy](https://www.justice.gov/jm/jm-9-48000-computer-fraud), [US Copyright Office AI materials](https://www.copyright.gov/ai/), [China Data Security Law](https://en.npc.gov.cn.cdurl.cn/2021-06/10/c_689311_2.htm) |
| Moving collected data | US hosting alone is not proof that subsequent transfers or processing are unrestricted. | Applicable outbound-transfer mechanisms can depend on data category, actor, volume, and exemptions. | Storing collected data abroad—or sending it to a foreign hosted embedding/LLM API—can create an additional transfer question. It does not follow that every download requires approval or that all data must stay in China. [PIPL Art. 38](https://en.npc.gov.cn.cdurl.cn/2021-12/29/c_694559_2.htm), [CAC 2024 provisions](https://www.cac.gov.cn/2024-03/22/c_1712776611775634.htm) |

The first row and “implication” column are engineering synthesis, not measurements of any specific website. Access may also vary by date, account, and session. No US or China target was scraped or benchmarked in this research.

## Two examples to make this concrete

**Example A — same product catalogue, different hosting:** suppose you have permission to collect a catalogue and the operator moves its origin from Virginia to Shanghai. If the HTML is identical, your selectors may remain identical. Your network timing can change. A CDN may serve a nearby cached copy, so an IP lookup alone does not reliably reveal the origin. If the site localizes responses, currency, inventory, or language can differ by visitor region. This is a hypothetical engineering example, not a claim about a particular retailer.

**Example B — public user reviews:** moving the same review site to a US server does not automatically remove obligations concerning people in mainland China. PIPL Article 3 describes circumstances in which processing outside China is within scope. A model predicting individual behavior raises different questions from an exercise using nonpersonal catalogue fields. Review text can include names, health details, or contact information even if you do not explicitly request those fields. [PIPL scope](https://en.npc.gov.cn.cdurl.cn/2021-12/29/c_694559.htm)

Your own country and organization also matter. If you operate the scraper in India, US and Chinese rules are not the only possible rules to consider. This guide does not determine the application of Indian law to a proposed project.

## Important corrections to common shortcuts

- **robots.txt is a crawler instruction file, not access authorization.** Its `Allow` directive is not an ML-training licence. An absent file is not a universal legal green light. [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)
- **US public-web scraping is not universally “legal.”** DOJ's CFAA charging policy narrows some theories based solely on terms violations, but it is prosecutorial guidance, not immunity from other claims or a grant of permission. [Current Justice Manual](https://www.justice.gov/jm/jm-9-48000-computer-fraud)
- **Do not use a 2021 PIPL webinar for current transfer thresholds.** The CAC's March 2024 provisions changed mechanisms and exemptions. The legal examples here are foundational, not an exhaustive audit of all developments through September 2026. [CAC provisions](https://www.cac.gov.cn/2024-03/22/c_1712776611775634.htm)
- **ICP filing is a hosting/operator issue in the Cloudflare video.** It is not a universal licence that a foreign scraper must obtain merely to fetch a page. [Cloudflare ICP documentation](https://developers.cloudflare.com/china-network/concepts/icp/)
- **Learning to respect security means building stop conditions.** Recommended beginner policy: stop on login/paywall barriers, persistent 403s, CAPTCHA challenges, or explicit operator objections; ask for permission or another data source. Proxies and browser automation do not settle authorization.

## A small regional experiment you can do legitimately

Use a site you control, or a site whose owner has approved the experiment. With the same page budget, compare two permitted execution regions and explicitly set/document language preferences. Record timestamp, final URL, status, latency, content hash, observed currency/language, and missing fields. Inspect differences before interpreting them as regional behavior. Keep raw comparison data only where its storage is permitted.

For ML, the key lesson is sampling bias: a model trained only on the version visible from one location may miss other languages, product ranges, or populations. Treat region as collection metadata and evaluate coverage rather than silently mixing inconsistent datasets.
