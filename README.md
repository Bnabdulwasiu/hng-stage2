# Profile API

A FastAPI service that enriches names with predicted gender, age, and nationality using third-party APIs (Genderize, Agify, Nationalize), stores the results, and exposes filtering, sorting, pagination, and natural language search.

---

## Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/profiles` | Create a profile by name |
| `GET` | `/api/profiles` | List profiles with filters, sorting, pagination |
| `GET` | `/api/profiles/search` | Natural language search |
| `GET` | `/api/profiles/{id}` | Get a single profile |
| `DELETE` | `/api/profiles/{id}` | Delete a profile |

---

## Natural Language Parsing

**Endpoint:** `GET /api/profiles/search?q=<query>`

The parser (`parse_query` in `utils.py`) is fully rule-based — no AI or LLMs. It normalizes the input to lowercase, strips punctuation, and applies keyword matching and regex patterns in sequence to extract filters.

### Supported Keywords & Mappings

**Gender**

| Keywords | Maps to |
|---|---|
| `male`, `males`, `man`, `men`, `boy`, `boys` | `gender=male` |
| `female`, `females`, `woman`, `women`, `girl`, `girls` | `gender=female` |

If both male and female keywords appear in the same query, no gender filter is applied.

**Age Group**

| Keywords | Maps to |
|---|---|
| `child`, `children` | `age_group=child` |
| `teenager`, `teenagers`, `teen`, `teens` | `age_group=teenager` |
| `adult`, `adults` | `age_group=adult` |
| `senior`, `seniors`, `elderly` | `age_group=senior` |
| `young`, `youth` | `min_age=16`, `max_age=24` (not a stored age group) |

> `young` is a special case — it maps to an age range (16–24) rather than a stored `age_group` value. If a stored age group keyword also appears (e.g. "young adults"), the age group takes priority and `young` is ignored.

**Explicit Age via Regex**

| Pattern | Maps to |
|---|---|
| `above 30`, `over 30`, `older than 30` | `min_age=30` |
| `below 25`, `under 25`, `younger than 25` | `max_age=25` |
| `between 20 and 35` | `min_age=20`, `max_age=35` |

**Country**

The parser first looks for trigger words (`from`, `in`, `of`) and extracts the phrase that follows, then resolves it using `pycountry.countries.lookup()`. If that fails, it scans tokens individually as a fallback.

| Example phrase | Maps to |
|---|---|
| `from nigeria` | `country_id=NG` |
| `in kenya` | `country_id=KE` |
| `from south africa` | `country_id=ZA` |

### Example Mappings

```
"young males from nigeria"         → gender=male, min_age=16, max_age=24, country_id=NG
"females above 30"                 → gender=female, min_age=30
"people from angola"               → country_id=AO
"adult males from kenya"           → gender=male, age_group=adult, country_id=KE
"male and female teenagers"        → age_group=teenager
"seniors in japan above 65"        → age_group=senior, country_id=JP, min_age=65
```

### Uninterpretable Queries

If no filters are extracted after full parsing, the API returns:
```json
{ "status": "error", "message": "Unable to interpret query" }
```

---

## Limitations & Known Edge Cases

**1. No negation support**
Queries like `"not from nigeria"` or `"excluding males"` are not handled. The negation word is ignored and the filter is applied as if it were positive.

**2. Short country codes are not matched**
Two-letter ISO codes like `"NG"` or `"KE"` in the query string are not resolved to countries. Only full country names work (e.g. `"nigeria"`, `"kenya"`).

**3. Ambiguous country names**
Some country names share common words (e.g. `"guinea"` could match Guinea, Guinea-Bissau, or Equatorial Guinea). `pycountry.lookup()` returns the first match — which may not be the intended one.

**4. Only the first age pattern is applied**
If a query contains multiple age expressions (e.g. `"above 20 and below 40"`), only the first regex match is used. `between X and Y` is the correct way to express a range.

**5. No spelling correction**
`"nigerria"`, `"femal"`, or `"teenagr"` will not match anything. The parser does exact keyword matching only.

**6. "Young" + explicit age conflict**
`"young males above 30"` sets `min_age=16, max_age=24` from `young`, then `min_age=30` from `above 30`. The explicit age regex overwrites the `young` range — but `max_age=24` is still set, producing a logically empty range (min > max). This is not validated at the parser level.

**7. Multi-word queries without trigger words**
`"south africa males"` without `"from"` / `"in"` will fail Strategy A and fall back to token scanning, where `"south"` and `"africa"` are scanned individually. `"africa"` is not a valid country in pycountry, so no country filter is applied.

**8. No support for multiple countries**
`"males from nigeria or ghana"` will only resolve the first country match found.
