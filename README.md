# nl-kalenders

Self-updating iCalendar feeds for Dutch holidays and school vacations, published with GitHub Pages and meant to be subscribed to from Proton Calendar (or any calendar app that takes a URL).

| Feed | URL |
|---|---|
| Vrije feestdagen | `https://jordanvoets.github.io/nl-kalenders/vrije-feestdagen.ics` |
| Overige feestdagen NL | `https://jordanvoets.github.io/nl-kalenders/overige-feestdagen-nl.ics` |
| Schoolvakanties Zuid | `https://jordanvoets.github.io/nl-kalenders/schoolvakanties-zuid.ics` |

## What's in them

- **Vrije feestdagen**: Nieuwjaarsdag, Eerste en Tweede Paasdag, Koningsdag, Hemelvaartsdag, Eerste en Tweede Pinksterdag, Eerste en Tweede Kerstdag. Days that fall on a weekend are marked as such, and these events show you as busy.
- **Overige feestdagen NL**: Goede Vrijdag, Bevrijdingsdag, Carnaval, Dodenherdenking, Moederdag, Vaderdag, Keti Koti, Prinsjesdag, Sinterklaasavond, the clock changes and similar days. These events show you as free.
- **Schoolvakanties Zuid**: every school vacation the Rijksoverheid publishes for regio Zuid, labelled as either fixed or advisory dates.

The holidays are calculated for the previous year through ten years ahead, so the window moves forward by itself. The school vacations come from the [Rijksoverheid open data API](https://www.rijksoverheid.nl/opendata/schoolvakanties). The last good response is kept in `data/schoolvakanties.json`, so the feed keeps working if the API is down.

## How it updates

`.github/workflows/publish.yml` runs on the 1st of every month, on every push to `main`, and when started by hand. Each run does four things:

1. Runs `generate.py`, which uses only the Python standard library.
2. Commits the school-vacation cache, but only when the data has changed. That's usually once a year, when a new school year is published.
3. Deploys `public/` to GitHub Pages.
4. Calls GitHub's "enable workflow" API on itself. GitHub turns off scheduled workflows in public repos after 60 days without activity, and this call resets that counter, so no keepalive commits are needed. GitHub doesn't document this behaviour. If the workflow is ever switched off anyway, re-enable it from the Actions tab.

Proton picks up changes from subscribed calendars every 8 to 16 hours.

## Changing things

- To change the region, edit `REGION` at the top of `generate.py` (`noord`, `midden` or `zuid`). The feed name follows the region.
- To change which days count as days off, edit `vrije_feestdagen()`. For other days, edit `overige_feestdagen()`.
- To run it locally: `python3 generate.py --out public`. Add `--offline` to use the cache instead of the API.
