# WorkshopTimers.com

A big fullscreen countdown timer for workshops, design sprints, meetings and classrooms, built to be read from the back of a room or over a Zoom or Teams screen share. It also does stopwatch, clock and Pomodoro modes. Use it at [workshoptimers.com](https://workshoptimers.com).

The whole app is one HTML file (`index.html`, about 480 KB with its fonts embedded) plus a small service worker (`sw.js`) that lets it open offline. There is no build step, no framework, no account and no server of our own.

## Where your data goes

Everything you set up (duration, label, theme, colours, logo, sounds, language) is stored in your browser's `localStorage` on your device and never sent to us. The keys are `wt_state_v3` (settings), `wt_run_v1` (a running or paused timer, so a refresh doesn't lose it), `wt_logo_v1`, `wt_font_v1`, `wt_license_v1` and `wt_onboarded_v1`.

You can take your setup with you: Settings → **Your settings file** saves it as `workshop-timer-settings.json` and loads it back on another computer. The file holds your settings and logo; it leaves out your licence key and any font you uploaded.

There are no analytics, no tracking cookies and no ads, and nothing is loaded from third-party servers. The app only talks to the network in two cases. GitHub Pages serves the page and, like any web host, logs access data such as your IP address. If you buy Pro and paste a licence key, the key and the label "Workshop Timer · activated" with the date go to [Dodo Payments](https://dodopayments.com), the payment provider, to check it. Voice alerts prefer speech voices that run on your device. The full [privacy policy](https://workshoptimers.com/datenschutz.html) has the details.

## Free and Pro

Everything except the extra themes is free: the timer, all four modes, three themes, all eight end sounds, voice alerts, every font plus font upload, your own colours and logo, settings files and every keyboard shortcut. A one-time Pro unlock (€5 or local equivalent, through Dodo Payments) will add the other 20 themes and their colour variants. Sales haven't opened yet, so for now the app shows Pro as coming soon and you can preview any theme for 15 seconds.

Once unlocked on a device, Pro keeps working offline; it is only removed if Dodo positively reports the key as invalid. To start selling, put the Dodo checkout link in `BUY_URL` near the top of the script in `index.html`.

## Run your own copy

Download `index.html` and `sw.js`, put them in the same folder, and either open `index.html` in a browser or serve the folder from any static host. Nothing else is needed. The service worker only registers over `https://` or `localhost`.

## Tests

`tests/` holds browser tests that run the real page in headless Chromium: every theme and mode, a timer surviving a refresh, the settings file round trip, what free users get, licence checks against mocked Dodo responses, keyboard and screen-reader basics, and the legal pages. GitHub Actions runs them on every push, and the site is only published to GitHub Pages when they all pass. To run them yourself:

```sh
pip install -r tests/requirements.txt
playwright install chromium
pytest
```

## Licence

The code is released under the [MIT licence](LICENSE), so you can use, change, fork and redistribute it, including commercially. The embedded fonts are separate works under the SIL Open Font License; [FONTS.md](FONTS.md) lists each one with its copyright.

## Keyboard

Space start/pause · R reset · F fullscreen · T next theme · M mute · ↑↓ ±1 min · ←→ ±10 sec · click the time, or Tab to it and press Enter, to type one (`15`, `10:30`, `1:00:00`).

## Limitations

- Settings live in one browser. A private window, cleared site data or a different browser starts from scratch unless you load a settings file.
- The first visit needs a network connection; after that, the installed app or a cached page opens offline.
- Browsers block sound until you click or press a key on the page. If you refresh while a timer is running, the countdown carries on, but the end sound may stay silent unless someone touches the page before it finishes.
- Voice alerts use your browser's built-in speech voices and are spoken in English only, whatever language the interface is in.
- Several themes (Lava, Aurora, Ocean, Orb and others) draw animated WebGL backgrounds that can be slow on old or low-power machines. Time Disc, the default, is light.
- Activating Pro on a new device needs a connection to Dodo Payments, and Dodo enforces a per-key device limit.
- The legal pages have not had a lawyer's review; the Impressum, AGB and Widerruf pages are still templates.
- There are no automated tests yet.

## Contact

Bugs and questions: [support@pigrosoft.com](mailto:support@pigrosoft.com). WorkshopTimers.com is made by Jeffrey Humble in Berlin; more of his projects are at [pigrosoft.com](https://pigrosoft.com).
