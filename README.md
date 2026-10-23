# WorkshopTimers.com

A big fullscreen countdown timer for workshops, design sprints, meetings and classrooms, built to be read from the back of a room or over a Zoom or Teams screen share. It also does stopwatch, clock and Pomodoro modes. Use it at [workshoptimers.com](https://workshoptimers.com).

The whole app is one HTML file (`index.html`, about 480 KB with its fonts embedded) plus a small service worker (`sw.js`) that lets it open offline. There is no build step, no framework, no account and no server of our own.

## Where your data goes

Everything you set up (duration, label, theme, colours, logo, sounds, language) is stored in your browser's `localStorage` on your device and never sent to us. The keys are `wt_state_v3` (settings), `wt_run_v1` (a running or paused timer, so a refresh doesn't lose it), `wt_logo_v1`, `wt_font_v1`, `wt_license_v1` and `wt_onboarded_v1`.

You can take your setup with you: Settings → **Your settings file** saves it as `workshop-timer-settings.json` and loads it back on another computer. The file holds your settings and logo; it leaves out your licence key and any font you uploaded.

There are no analytics, no tracking cookies and no ads. The app only talks to the network in two cases. GitHub Pages serves the page and, like any web host, logs access data such as your IP address. If you buy Pro and paste a licence key, the key and a short device label (your browser's platform name and today's date) go to [Polar](https://polar.sh), the payment provider, to check it.

## Free and Pro

The timer, all four modes, three themes, all eight end sounds and every keyboard shortcut are free. A one-time Pro unlock (€5 or local equivalent, through Polar) adds the other themes and their colour variants, voice alerts, extra fonts and font upload, and your own colours and logo. Once unlocked on a device, Pro keeps working offline; it is only removed if Polar positively reports the key as invalid or revoked.

## Run your own copy

Download `index.html` and `sw.js`, put them in the same folder, and either open `index.html` in a browser or serve the folder from any static host. Nothing else is needed. The service worker only registers over `https://` or `localhost`.

Note that there is no open-source licence yet, so the code is currently all rights reserved even though the repository is public.

## Keyboard

Space start/pause · R reset · F fullscreen · T next theme · M mute · ↑↓ ±1 min · ←→ ±10 sec · click the time to type one (`15`, `10:30`, `1:00:00`).

## Limitations

- Settings live in one browser. A private window, cleared site data or a different browser starts from scratch unless you load a settings file.
- The first visit needs a network connection; after that, the installed app or a cached page opens offline.
- Browsers block sound until you click or press a key on the page. If you refresh while a timer is running, the countdown carries on, but the end sound may stay silent unless someone touches the page before it finishes.
- Voice alerts use your browser's built-in speech voices and are spoken in English only, whatever language the interface is in.
- Several themes (Lava, Aurora, Ocean, Orb and others) draw animated WebGL backgrounds that can be slow on old or low-power machines. Time Disc, the default, is light.
- Activating Pro on a new device needs a connection to Polar, and Polar enforces a per-key device limit.
- The German legal pages (Impressum, Datenschutz, AGB, Widerruf) are still placeholder templates.
- There are no automated tests yet.

## Contact

Bugs and questions: [support@pigrosoft.com](mailto:support@pigrosoft.com). WorkshopTimers.com is made by [PigroSoft](https://pigrosoft.com) in Berlin.
